import asyncio
import pickle
from pathlib import Path
import yaml
import os
import aiohttp
import pandas as pd
import requests
from lxml.html import fromstring
from pdfrw import PdfReader, PdfWriter
from typing import List

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship
from datetime import date

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

with open('config/geschaeftstypen.yaml', 'r') as file:
    geschaeftstypen = yaml.safe_load(file)


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
    __tablename__ = 'members'

    memberid: Mapped[int] = mapped_column(Integer, nullable=False, primary_key=True, unique=True)
    memberFirstName: Mapped[str] = mapped_column(String(50), unique=False, nullable=False)
    memberLastName: Mapped[str] = mapped_column(String(50), unique=False, nullable=False)

class FileTable(BaseTable):
    __tablename__ = 'files'

    fileid: Mapped[str] = mapped_column(String(100), nullable=False, primary_key=True, unique=True)
    docid: Mapped[str] = mapped_column(String(100), nullable=False)
    path: Mapped[str] = mapped_column(String(250), nullable=False)

class GeschaeftTable(BaseTable):
    __tablename__ = 'geschaefte'

    gesid: Mapped[str] = mapped_column(String(50), nullable=False, primary_key=True, unique=True)
    docs: Mapped[List['DocumentTable']] = relationship(back_populates='ges')
    memberid: Mapped[int] = mapped_column(Integer, nullable=False)
    ges_type: Mapped[int] = mapped_column(Integer, nullable=True)
    ges_status: Mapped[int] = mapped_column(Integer, nullable=True)
    ges_date: Mapped[str] = mapped_column(String(10), nullable=True)
    url: Mapped[str] = mapped_column(String(250), nullable=False)

class DocumentTable(BaseTable):
    __tablename__ = 'documents'

    docid: Mapped[str] = mapped_column(String(10), nullable=False, primary_key=True, unique=True)
    gesid: Mapped[str] = mapped_column(ForeignKey('geschaefte.gesid'))
    ges: Mapped['GeschaeftTable'] = relationship(back_populates='docs')
    doc_type: Mapped[str] = mapped_column(String(50))
    creator: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[str] = mapped_column(String(10))
    status: Mapped[int] = mapped_column(Integer)
    details: Mapped[str] = mapped_column(String(250))
    url: Mapped[str] = mapped_column(String(250))

class grossrat:
    def __init__(self, memberid: int):
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
            "url": str,
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
            "doc_date": str,
            "details": str,
            "url": str,
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
        self.db_folder = 'db'
        # self.members = pd.DataFrame(columns={'gesid':str, 'memberid': int, 'url': str})
        # self.documents =
        # self.files =

    def create_database(self):
        Path(self.db_folder).mkdir(parents=True, exist_ok=True)
        Path(f'{self.db_folder}/grossrat.sqlite3').touch(exist_ok=True)
        engine = create_engine(f'sqlite:///{self.db_folder}/grossrat.sqlite3')
        BaseTable.metadata.create_all(engine)

    def get_member_page(self):
        self.page_resp = requests.get(
            "https://grosserrat.bs.ch/mitglieder/" + str(self.memberid)
        )
        return self.page_resp

    def create_linklist(self):
        """
        Extracts links to geschaefte from member page
        :return:
        """
        tree = fromstring(self.page_resp.text)
        elements = tree.xpath("//*[@id='table_geschaefte']/tbody/tr")
        self.geschaefte["ges_date"] = [elem.getchildren()[0].text for elem in elements]
        self.geschaefte["gesid"] = [elem.getchildren()[1].getchildren()[0].text for elem in elements]
        self.geschaefte["url"] = [
            f'https://grosserrat.bs.ch{elem.getchildren()[1].getchildren()[0].attrib["href"]}' for elem in elements
        ]
        self.geschaefte["memberid"] = self.memberid

    def save_geschaefte(self):
        """
        Saves geschaefte to SQLite database
        :return:
        """
        db_engine = create_engine(f"sqlite:///{self.db_folder}/grossrat.sqlite3")
        with db_engine.begin() as connection:
            self.geschaefte.to_sql(
                name="geschaefte", con=connection, index=False, if_exists="append"
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
                dtype={"gesid": str, "memberid": int, "geschaeftstyp": int, "status": int, "ges_date": str, "url": str},
            )

    def get_dok_details(self):
        """
        Loads the geschaeft detail pages
        :return:
        """
        self.html_list = asyncio.run(get_dok_details_async(self.geschaefte["url"]))

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


    def extract_ges_dok_info_2(self):
        i = 0
        for t in self.html_list:
            tree = fromstring(t)
            ges_details = tree.xpath("//*[@id='detail_table_geschaeft_resumee']")
            ges_nr = ges_details[0].getchildren()[0].getchildren()[1].text
            #%TODO: Hier mit Geschäftstyp weiterfahren
            dok_no = tree.xpath("//*[@headers='th_dokno']")
            ges_title_total_list.append(
                tree.xpath("//*[@class='h3 mobile-h4  title']")[0].text
            )  # Append Geschäftstitel
            dok_title_list = [
                tree.xpath("//*[@headers='th_titel']")[x].getchildren()[0].text
                for x in range(len(dok_no))
            ]
            if dok_title_list[0]:
                dok_nr_total_list.extend(
                    [dok_no[x].getchildren()[0].text for x in range(len(dok_no))]
                )
                dok_title_total_list.extend(dok_title_list)
                dok_link_total_list.extend(
                    [
                        dok_no[x].getchildren()[0].attrib["href"]
                        for x in range(len(dok_no))
                    ]
                )  # Extends dok_link_total_list with dok_link_list
                dok_date_total_list.extend(
                    [
                        tree.xpath("//*[@headers='th_datum']")[x].text
                        for x in range(len(dok_no))
                    ]
                )  # Extends dok_date_total_list with dok_date_list
            else:
                for lst in [
                    dok_nr_total_list,
                    dok_title_total_list,
                    dok_link_total_list,
                    dok_date_total_list,
                ]:
                    lst.append(None)
            i += 1
        for doknr in dok_nr_total_list:
            if type(doknr) == str:
                ges_nr_total_list.append(doknr[:-3])
            else:
                ges_nr_total_list.append(doknr)

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
                ges_uebersicht.loc[
                    ges_uebersicht["Geschäftsnummer"] == ges_nr, key
                ] = value
            return ges_uebersicht
