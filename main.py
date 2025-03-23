import asyncio
import pickle
from pathlib import Path
from typing import List

import aiohttp
import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup as bs
from lxml.html import fromstring
from sqlalchemy import create_engine, Integer, String, ForeignKey
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
    async with session.get(url, headers={"User-Agent": "XY"}) as response:
        resp = await response.read()
    return resp


async def get_dok_details_async(link_list):
    async with aiohttp.ClientSession() as session:
        tasks = [get_resp_async(url=url, session=session) for url in link_list]
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
        pass

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
        with open("config/geschaeftstypen.yaml", "r") as file:
            self.geschaeftstypen_types = yaml.safe_load(file)
            self.geschaeftstypen = pd.DataFrame(
                self.geschaeftstypen_types.values(),
                index=self.geschaeftstypen_types.keys(),
            )
        # self.members = pd.DataFrame(columns={'gesid':str, 'memberid': int, 'url': str})
        # self.documents =
        # self.files =

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
        db_engine = create_engine(f"sqlite:///{self.db_folder}/grossrat.sqlite3")
        self.documents.to_sql(
            name="documents",
            con=db_engine,
            index=False,
            if_exists="replace",
            chunksize=1000,
        )

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
        with open(Path("dok_detail_list.pkl"), "wb") as f:
            pickle.dump(self.html_list, f)

    def get_dok_details_from_pickle(self):
        with open(Path("dok_detail_list.pkl"), "rb") as f:
            self.html_list = pickle.load(f)

    def extract_doc_details(self):
        extract_value = lambda x: x[0]
        extract_link = lambda x: x[1]
        # self.geschaefte = pd.concat(pd.read_html(self.member_page_url, attrs={'id': 'table_geschaefte'}, extract_links='body', converters={0: extract_value, 2: extract_value}))
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

    def create_ges_uebersicht(self):
        ges_uebersicht = pd.DataFrame(
            data={
                "Geschäftsnummer": self.geschaefte["gesid"],
                "Geschäfts-URL": self.geschaefte["url"],
                "Geschäftstitel": ges_title_total_list,
            },
            columns=[
                "Geschäftsnummer",
                "Geschäfts-URL",
                "Geschäftstyp",
                "Urheber",
                "Beginn",
                "Status",
            ],
        )
        for ges_nr, url in zip(
            ges_uebersicht["Geschäftsnummer"], ges_uebersicht["Geschäfts-URL"]
        ):
            page_resp = requests.get(url)
            tree = fromstring(page_resp.text)
            ges_detail = tree.xpath("//*[@id='detail_table_geschaeft_resumee']/tr")
            keylist, valuelist = [], []
            for elem in ges_detail:
                child_list = elem.getchildren()
                if child_list[0].text in ["Geschäftsnummer", "Geschäftstyp", "Beginn"]:
                    keylist.append(child_list[0].text)
                    valuelist.append(child_list[1].text)
                elif elem.getchildren()[1].getchildren()[0].text:
                    keylist.append(child_list[0].text)
                    valuelist.append(elem.getchildren()[1].getchildren()[0].text)
                elif elem.getchildren()[1].getchildren()[0].getchildren()[0].text:
                    keylist.append(child_list[0].text)
                    valuelist.append(
                        elem.getchildren()[1]
                        .getchildren()[0]
                        .getchildren()[0]
                        .text.lstrip()
                    )
            ges_dict = {
                k: v
                for (k, v) in zip(keylist, valuelist)
                if k not in ["Geschäftsnummer"]
            }
            for key, value in ges_dict.items():
                ges_uebersicht.loc[ges_uebersicht["Geschäftsnummer"] == ges_nr, key] = (
                    value
                )
            return ges_uebersicht
