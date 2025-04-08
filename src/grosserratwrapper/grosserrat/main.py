import asyncio
import io
import pickle
from datetime import datetime
from pathlib import Path
from typing import List

from ..config import geschaeftstypen

import aiohttp
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
from pypdf import PdfReader, PdfWriter
from sqlalchemy import ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship
from sqlalchemy.testing.schema import mapped_column

# Basics
(
    dok_nr_total_list,
    ges_nr_total_list,
    ges_title_total_list,
    dok_title_total_list,
    dok_link_total_list,
    dok_date_total_list,
) = [[] for _ in range(6)]


async def get_resp_async(url, session):
    async with session.get(url, headers={"User-Agent": "XY"}, timeout=30) as response:
        resp = await response.read()
    return resp


sem = asyncio.Semaphore(3)


async def safe_download(url, session):
    async with sem:  # semaphore limits num of simultaneous downloads
        return await get_resp_async(url, session)


async def get_dok_details_async(link_list):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(30)) as session:
        tasks = [safe_download(url=url, session=session) for url in link_list]
        results = await asyncio.gather(*tasks)
    return results


class BaseTable(DeclarativeBase):
    pass


class MemberTable(BaseTable):
    __tablename__ = "members"

    memberid: Mapped[int] = mapped_column(
        Integer, nullable=False, primary_key=True, unique=True
    )
    memberFirstName: Mapped[str] = mapped_column(
        String(50), unique=False, nullable=False
    )
    memberLastName: Mapped[str] = mapped_column(
        String(50), unique=False, nullable=False
    )


class FileTable(BaseTable):
    __tablename__ = "files"

    fileid: Mapped[str] = mapped_column(
        String(100), nullable=False, primary_key=True, unique=True
    )
    docid: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str] = mapped_column(String(250), nullable=False)


class GeschaeftTable(BaseTable):
    __tablename__ = "geschaefte"

    gesid: Mapped[str] = mapped_column(
        String(50), nullable=False, primary_key=True, unique=True
    )
    docs: Mapped[List["DocumentTable"]] = relationship(back_populates="ges")
    memberid: Mapped[int] = mapped_column(Integer, nullable=False)
    ges_titel: Mapped[str] = mapped_column(String(250), nullable=True)
    ges_type: Mapped[int] = mapped_column(Integer, nullable=True)
    ges_status: Mapped[int] = mapped_column(Integer, nullable=True)
    ges_date: Mapped[str] = mapped_column(String(10), nullable=True)
    ges_url: Mapped[str] = mapped_column(String(250), nullable=False)


class DocumentTable(BaseTable):
    __tablename__ = "documents"

    docid: Mapped[str] = mapped_column(
        String(10), nullable=False, primary_key=True, unique=True
    )
    gesid: Mapped[str] = mapped_column(ForeignKey("geschaefte.gesid"))
    ges: Mapped["GeschaeftTable"] = relationship(back_populates="docs")
    doc_type: Mapped[str] = mapped_column(String(50))
    creator: Mapped[int] = mapped_column(Integer)
    doc_date: Mapped[str] = mapped_column(String(10))
    doc_url: Mapped[str] = mapped_column(String(250))


class GrosserRat:
    def __init__(self):
        members_overview_post_params = {
            "filter[reiter]": "MIT",
            "filter[search]": "",
            "filter[section]": "",
            "list[mit_limit]": "",
            "list[ordering]": "name",
            "list[direction]": "ASC",
            "template": "MITcards",
            "task": "",
            "boxchecked": "0",
            # 'a7a667e02dee5f6fcbc099b9a31a68ce':'1',
            "list[fullordering]": "null+ASC",
        }
        members_overview_post_params = members_overview_post_params | {
            "filter[such_ehemalige_mit]": "1",
            "filter[such_von_mit]": "2005-02-01",
            "filter[such_bis_mit]": "2025-03-15",
        }
        members_overview_html = requests.post(
            "https://grosserrat.bs.ch/mitglieder", data=members_overview_post_params
        ).text
        members_overview_soup = bs(members_overview_html, "lxml")
        name_list = [
            row.get_text()
            for row in members_overview_soup.find_all(
                "h6", attrs={"class": "person-name"}
            )
        ]
        memberid_list = [
            int(row.parent.get("data-uni_nr"))
            for row in members_overview_soup.find_all("div", attrs={"class": "person"})
        ]
        self.members_df = pd.DataFrame(
            data={"membername": name_list}, index=memberid_list
        ).sort_index()
        self.members_df.index.name = "memberid"
        # %TODO: implement scraping member infos from member pages
        # %TODO: implement function to save members to db

    def get_members(self, nur_aktuell=True):
        members_overview_post_params = {
            "filter[reiter]": "MIT",
            "filter[search]": "",
            "filter[section]": "",
            "list[mit_limit]": "",
            "list[ordering]": "name",
            "list[direction]": "ASC",
            "template": "MITcards",
            "task": "",
            "boxchecked": "0",
            # 'a7a667e02dee5f6fcbc099b9a31a68ce':'1',
            "list[fullordering]": "null+ASC",
        }
        if nur_aktuell is False:
            members_overview_post_params = members_overview_post_params | {
                "filter[such_ehemalige_mit]": "1",
                "filter[such_von_mit]": "2005-02-01",
                "filter[such_bis_mit]": "2025-03-15",
            }
        members_overview_html = requests.post(
            "https://grosserrat.bs.ch/mitglieder", data=members_overview_post_params
        ).text
        members_overview_soup = bs(members_overview_html, "lxml")
        name_list = [
            row.get_text()
            for row in members_overview_soup.find_all(
                "h6", attrs={"class": "person-name"}
            )
        ]
        memberid_list = [
            int(row.parent.get("data-uni_nr"))
            for row in members_overview_soup.find_all("div", attrs={"class": "person"})
        ]
        self.members_df = pd.DataFrame(
            data={"membername": name_list}, index=memberid_list
        ).sort_index()
        self.members_df.index.name = "memberid"
        return self.members_df


class Grossrat(GrosserRat):
    def __init__(self, memberid: int):
        super().__init__()
        self.html_list = None
        self.link_list = None
        self.gsnr_list = None
        self.page_resp = None
        self.memberid = memberid
        self.member_name = self.members_df.loc[self.memberid, "membername"]
        self.cols_geschaefte = {
            "gesid": str,
            "memberid": int,
            "ges_type": int,
            "ges_status": int,
            "ges_date": str,
            "ges_url": str,
        }
        self.cols_members = {
            "memberid": int,
            "memberFirstName": str,
            "memberLastName": str,
        }
        self.cols_documents = {
            "docid": str,
            "gesid": str,
            "creator": int,
            "doc_type": str,
            "doc_date": str,
            "doc_url": str,
        }
        self.cols_files = {"fileid": str, "docid": str, "path": str}
        self.geschaefte = pd.DataFrame(columns=list(self.cols_geschaefte.keys()))
        self.geschaefte = self.geschaefte.astype(self.cols_geschaefte)
        del self.cols_geschaefte
        self.documents = pd.DataFrame(columns=list(self.cols_documents.keys()))
        self.documents = self.documents.astype(self.cols_documents)
        del self.cols_documents
        self.members = pd.DataFrame(columns=list(self.cols_members.keys()))
        self.members = self.members.astype(self.cols_members)
        del self.cols_members
        self.files = pd.DataFrame(columns=list(self.cols_files.keys()))
        self.files = self.files.astype(self.cols_files)
        del self.cols_files
        self.db_folder = "db"
        self.geschaeftstypen = pd.DataFrame(
            geschaeftstypen.values(),
            index=geschaeftstypen.keys(),
        )

    def create_database(self):
        Path(self.db_folder).mkdir(parents=True, exist_ok=True)
        Path(f"{self.db_folder}/grossrat.sqlite3").touch(exist_ok=True)
        engine = create_engine(f"sqlite:///{self.db_folder}/grossrat.sqlite3")
        BaseTable.metadata.create_all(engine)

    def get_member_page(self):
        self.member_page_url = "https://grosserrat.bs.ch/mitglieder/" + str(
            self.memberid
        )
        self.page_resp = requests.get(self.member_page_url)
        return self.page_resp

    def create_linklist(self):
        """
        Extracts links to geschaefte from member page
        :return:
        """

        def first_element(x):
            return x[0]

        self.geschaefte = pd.concat(
            pd.read_html(
                self.member_page_url,
                attrs={"id": "table_geschaefte"},
                extract_links="body",
                converters={0: first_element, 2: first_element},
            )
        )
        self.geschaefte[["gesid", "ges_url"]] = self.geschaefte[1].apply(
            lambda x: pd.Series(x)
        )
        self.geschaefte = self.geschaefte.rename(
            columns={0: "ges_date", 2: "ges_titel"}
        )[["gesid", "ges_date", "ges_titel", "ges_url"]]
        self.geschaefte = self.geschaefte[["gesid", "ges_date", "ges_titel", "ges_url"]]
        self.geschaefte["memberid"] = self.memberid

    def save_geschaefte(self):
        """
        Saves geschaefte to SQLite database
        :return:
        """
        db_engine = create_engine(f"sqlite:///{self.db_folder}/grossrat.sqlite3")
        self.geschaefte.to_sql(
            name="geschaefte",
            con=db_engine,
            index=False,
            if_exists="replace",
            chunksize=1000,
        )

    def load_geschaefte(self):
        """
        Loads geschaefte from SQLite database
        :return:
        """
        db_engine = create_engine(f"sqlite:///{self.db_folder}/grossrat.sqlite3")
        with db_engine.begin() as connection:
            self.geschaefte = pd.read_sql(
                "geschaefte",
                con=connection,
                dtype={
                    "gesid": str,
                    "memberid": int,
                    "geschaeftstyp": int,
                    "status": int,
                    "ges_date": str,
                    "url": str,
                },
            )

    def save_documents(self):
        """
        Saves documents to SQLite database
        :return:
        """
        self.manually_correct_documents()
        db_engine = create_engine(f"sqlite:///{self.db_folder}/grossrat.sqlite3")
        self.documents.to_sql(
            name="documents",
            con=db_engine,
            index=False,
            if_exists="replace",
            chunksize=1000,
        )

    def manually_correct_documents(self):
        self.documents.loc[
            self.documents.doc_url
            == "https://grosserrat.bs.ch/dokumente/100404/000000404382.pdf",
            "gesid",
        ] = "23.5153"
        self.documents.loc[
            self.documents.doc_url
            == "https://grosserrat.bs.ch/dokumente/100404/000000404382.pdf",
            "docid",
        ] = "23.5153.01"
        self.documents.loc[
            self.documents.doc_url
            == "https://grosserrat.bs.ch/dokumente/100397/000000397037.pdf",
            "docid",
        ] = "22.5212.01"
        self.documents.loc[
            self.documents.gesid == "21.1562",
            "docid",
        ] = "21.5562.02"
        self.documents.loc[
            self.documents.gesid == "21.1562",
            "gesid",
        ] = "21.5562"
        self.documents.loc[
            self.documents.gesid == "15.4090",
            "gesid",
        ] = "15.5090"
        self.documents.loc[
            self.documents.docid == "15.4090.02",
            "docid",
        ] = "15.5090.02"
        self.documents.loc[
            self.documents.docid == "14.5404.01",
            "docid",
        ] = "14.5304.01"
        self.documents.loc[
            self.documents.gesid == "14.5404",
            "gesid",
        ] = "14.5304"
        self.geschaefte.loc[
            self.geschaefte.gesid == "14.5404",
            "gesid",
        ] = "14.5304"
        self.documents.loc[
            self.documents.docid == "14.5403.02",
            "docid",
        ] = "14.5303.02"
        self.documents.loc[
            self.documents.gesid == "14.5403",
            "gesid",
        ] = "14.5303"
        # %TODO: 14.5303.02 kreiert immer noch Probleme: An error occurred: No connection adapters were found for 'docid\n14.5303.02    https://grosserrat.bs.ch/dokumente/100378/0000...\n14.5303.02    https://grosserrat.bs.ch/dokumente/100378/0000...\nName: doc_url, dtype: object'

    def load_documents(self):
        """
        Loads documents from SQLite database
        :return:
        """
        db_engine = create_engine(f"sqlite:///{self.db_folder}/grossrat.sqlite3")
        with db_engine.begin() as connection:
            self.documents = pd.read_sql(
                "documents",
                con=connection,
                dtype={
                    "docid": str,
                    "gesid": str,
                    "creator": str,
                    "doc_type": str,
                    "doc_date": str,
                    "doc_url": str,
                },
            )

    def get_dok_details(self):
        """
        Loads the geschaeft detail pages
        :return:
        """
        self.html_list = asyncio.run(
            get_dok_details_async(
                "https://grosserrat.bs.ch/" + self.geschaefte["ges_url"]
            )
        )

    def save_dok_details_to_pickle(self):
        """
        Saves geschaeft detail pages to pickle
        :return:
        """
        with open(Path("../../../dok_detail_list.pkl"), "wb") as f:
            pickle.dump(self.html_list, f)

    def get_dok_details_from_pickle(self):
        with open(Path("../../../dok_detail_list.pkl"), "rb") as f:
            self.html_list = pickle.load(f)

    def extract_doc_details(self):
        def extract_value(x):
            return x[0]

        ges_details_list = [
            pd.read_html(pd_from_html, attrs={"id": "detail_table_geschaeft_resumee"})[
                0
            ].T.iloc[1]
            for pd_from_html in self.html_list
        ]
        ges_details = (
            pd.concat(ges_details_list, axis=1)
            .transpose()
            .rename(columns={0: "gesid", 1: "ges_type", 4: "ges_status"})
        )
        self.geschaefte[["ges_type", "ges_status"]] = pd.merge(
            self.geschaefte[["gesid"]],
            ges_details[["gesid", "ges_type", "ges_status"]],
            on="gesid",
            how="left",
        )[["ges_type", "ges_status"]]
        self.geschaefte["ges_type"] = (
            self.geschaefte["ges_type"]
            .replace(
                {
                    value: int(key)
                    for key, value in zip(
                        self.geschaeftstypen.index.tolist(),
                        self.geschaeftstypen[0].values.tolist(),
                    )
                }
            )
            .fillna(99)
        )
        self.geschaefte["ges_type"] = self.geschaefte["ges_type"].astype(int)
        dok_link_list = [
            pd.read_html(
                pd_from_html,
                attrs={"id": "detail_table_geschaeft_dokumente"},
                extract_links="body",
                converters={0: extract_value, 1: extract_value},
            )[0]
            for pd_from_html in self.html_list
        ]
        dok_details = pd.concat(dok_link_list, axis=0).rename(
            columns={"Nummer": "docid", "Datum": "doc_date", "Titel": "doc_type"}
        )
        dok_details.index = pd.RangeIndex(0, len(dok_details))
        dok_details[["doc_type", "doc_url"]] = pd.DataFrame(
            dok_details["doc_type"].tolist()
        )
        dok_details["gesid"] = dok_details.docid.str.extract(pat=r"^(\d+\.\d+)")
        dok_details["creator"] = self.memberid
        self.documents[
            ["docid", "doc_date", "doc_type", "doc_url", "gesid", "creator"]
        ] = pd.merge(self.documents[["docid"]], dok_details, how="right", on="docid")

    def download_pdfs(self):
        docid_counts = self.documents.docid.value_counts()
        self.manually_correct_documents()
        for doc in self.documents.loc[
            self.documents.docid.isin(
                docid_counts.loc[docid_counts == 1].index.tolist()
            ),
            "docid",
        ]:
            try:
                re = requests.get(self.documents.set_index("docid").at[doc, "doc_url"])
                pdf_file = io.BytesIO(re.content)
                reader = PdfReader(pdf_file)
                writer = PdfWriter(reader)
                if "Text" in self.documents.set_index("docid").at[doc, "doc_type"]:
                    folder = "Text"
                elif (
                    self.documents.set_index("docid").at[doc, "doc_type"]
                    == "Schreiben des RR"
                ):
                    folder = "Antwort"
                else:
                    folder = "Diverses"
                with open(
                    f"pdfs/{folder}/{doc.replace('.', '_')}.pdf", "wb"
                ) as newfile:
                    # Autor taken from superclass's member_df
                    writer.add_metadata(
                        {
                            "/Author": self.members_df.at[self.memberid, "membername"],
                            "/Title": self.geschaefte.set_index("gesid").at[
                                self.documents.set_index("docid").at[doc, "gesid"],
                                "ges_titel",
                            ],
                            "/Subject": self.geschaeftstypen.at[
                                self.geschaefte.set_index("gesid").at[
                                    self.documents.set_index("docid").at[doc, "gesid"],
                                    "ges_type",
                                ],
                                0,
                            ],
                            "/Keywords": "Keywords",
                            "/CreationDate": self.documents.set_index("docid").at[
                                doc, "doc_date"
                            ],
                            "/ModDate": datetime.today().strftime("%d.%m.%Y"),
                            "/Creator": self.members_df.at[self.memberid, "membername"],
                            "/GeschaeftsId": self.documents.set_index("docid").at[
                                doc, "gesid"
                            ],
                            "/DokumentId": doc,
                        }
                    )
                    writer.write(newfile)
            except Exception as e:
                print("An error occurred:", e)
                print(
                    f"Doc-Url: {self.documents.set_index('docid').at[doc, 'doc_url']}"
                )
