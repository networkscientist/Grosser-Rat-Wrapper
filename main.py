import asyncio
import pickle
from pathlib import Path

import aiohttp
import pandas as pd
import requests
from lxml.html import fromstring
from pdfrw import PdfReader, PdfWriter

# Basics
dok_nr_total_list, ges_nr_total_list, ges_title_total_list, dok_title_total_list, dok_link_total_list, dok_date_total_list = [
    [] for _ in range(6)]


def get_member_page(member_nr):
    page_resp = requests.get("https://grosserrat.bs.ch/mitglieder/" + member_nr)
    return page_resp


def create_linklist(page_resp):
    tree = fromstring(page_resp.text)
    elements = tree.xpath("//*[@id='table_geschaefte']/tbody/tr/td/a")
    el = tree.xpath("//*[@id='table_geschaefte']/tbody/tr")
    gsnr_list = [elem.text for elem in elements]
    link_list = [f'https://grosserrat.bs.ch{elem.attrib["href"]}' for elem in elements]
    return gsnr_list, link_list


async def get(url, session):
    async with session.get(url, headers={"User-Agent": "XY"}) as response:
        resp = await response.read()
    return resp


async def get_dok_details(link_list):
    async with aiohttp.ClientSession() as session:
        tasks = [get(url=url, session=session) for url in link_list]
        print(*tasks)
        results = await asyncio.gather(*tasks)
    return results


def extract_ges_dok_info(ges_html_list):
    tree = fromstring(ges_html_list[1221])
    ges_details = tree.xpath("//*[@id='detail_table_geschaeft_resumee']")
    ges_nr = ges_details[0].getchildren()[0].getchildren()[1].text
    ges_typ = ges_details[0].getchildren()[1].getchildren()[1].text
    ges_creator = ges_details[0].getchildren()[2].getchildren()[1].getchildren()[0].text
    ges_start = ges_details[0].getchildren()[3].getchildren()[1].text
    ges_status = ges_details[0].getchildren()[4].getchildren()[1].getchildren()[0].getchildren()[
        0].text.lstrip().rstrip()
    dok_details = tree.xpath("//*[@id='detail_table_geschaeft_dokumente']")
    dok_no = tree.xpath("//*[@headers='th_dokno']")
    dok_nr_list = [dok_no[x].getchildren()[0].text for x in range(len(dok_no))]
    dok_link_list = [dok_no[x].getchildren()[0].attrib["href"] for x in range(len(dok_no))]
    dok_date_list = [tree.xpath("//*[@headers='th_datum']")[x].text for x in range(len(dok_no))]
    dok_title_list = [tree.xpath("//*[@headers='th_titel']")[x].getchildren()[0].text for x in range(len(dok_no))]


def extract_ges_dok_info_2(ges_html_list):
    i = 0
    for t in ges_html_list:
        print(i)
        tree = fromstring(t)
        ges_details = tree.xpath("//*[@id='detail_table_geschaeft_resumee']")
        ges_nr = ges_details[0].getchildren()[0].getchildren()[1].text
        dok_no = tree.xpath("//*[@headers='th_dokno']")
        ges_title_total_list.append(tree.xpath("//*[@class='h3 mobile-h4  title']")[0].text)  #Append Geschäftstitel
        dok_title_list = [tree.xpath("//*[@headers='th_titel']")[x].getchildren()[0].text for x in range(len(dok_no))]
        if dok_title_list[0]:
            dok_nr_total_list.extend([dok_no[x].getchildren()[0].text for x in range(len(dok_no))])
            dok_title_total_list.extend(dok_title_list)
            dok_link_total_list.extend([dok_no[x].getchildren()[0].attrib["href"] for x in
                                        range(len(dok_no))])  # Extends dok_link_total_list with dok_link_list
            dok_date_total_list.extend([tree.xpath("//*[@headers='th_datum']")[x].text for x in
                                        range(len(dok_no))])  # Extends dok_date_total_list with dok_date_list
        else:
            for lst in [dok_nr_total_list, dok_title_total_list, dok_link_total_list, dok_date_total_list]:
                lst.append(None)
        i += 1
    for doknr in dok_nr_total_list:
        if type(doknr) == str:
            ges_nr_total_list.append(doknr[:-3])
        else:
            ges_nr_total_list.append(doknr)


def create_doc_details():
    doc_details_dict = {
        "Geschäftsnummer": ges_nr_total_list,
        "Doknummer": dok_nr_total_list,
        "Titel": dok_title_total_list,
        "URL": dok_link_total_list,
        "Datum": dok_date_total_list
    }
    doc_details = pd.DataFrame(columns=["Geschäftsnummer", "Doknummer", "Titel", "URL", "Datum"], data=doc_details_dict)
    doc_details["Datum"] = pd.to_datetime(doc_details["Datum"], format='%d.%m.%Y', errors="coerce")
    return doc_details
    #At this point, we have the dataframe with all the pdf links


def create_ges_uebersicht():
    ges_uebersicht = pd.DataFrame(
        data={"Geschäftsnummer": gsnr_list, "Geschäfts-URL": link_list, "Geschäftstitel": ges_title_total_list},
        columns=["Geschäftsnummer", "Geschäfts-URL", "Geschäftstyp", "Urheber", "Beginn", "Status"])
    for ges_nr, url in zip(ges_uebersicht["Geschäftsnummer"], ges_uebersicht["Geschäfts-URL"]):
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
                valuelist.append(elem.getchildren()[1].getchildren()[0].getchildren()[0].text.lstrip())
        ges_dict = {k: v for (k, v) in zip(keylist, valuelist) if k not in ["Geschäftsnummer"]}
        for key, value in ges_dict.items():
            ges_uebersicht.loc[ges_uebersicht["Geschäftsnummer"] == ges_nr, key] = value
        return ges_uebersicht


# ges_uebersicht.to_pickle(Path("/home/me/PycharmProjects/Grosser-Rat-Wrapper/tmp.gz"))
# ges_uebersicht = pd.read_pickle(Path("/home/me/PycharmProjects/Grosser-Rat-Wrapper/tmp.gz"))
ges_uebersicht = create_ges_uebersicht()
ges_uebersicht["Geschäftstitel"] = ges_title_total_list

doc_details = create_doc_details()
combi = doc_details.set_index("Geschäftsnummer").join(ges_uebersicht.set_index("Geschäftsnummer"))
# combi.to_pickle(Path("/home/me/PycharmProjects/Grosser-Rat-Wrapper/combi.gz"))
combi = pd.read_pickle(Path("/home/me/PycharmProjects/Grosser-Rat-Wrapper/combi.gz"))
#Now we have all that we need to download all the docs
combi = combi.reset_index().set_index(["Doknummer"], drop=False).dropna(subset="URL")


def download_pdf(data):
    # Do the PDF downloads
    url = data["URL"]
    response = requests.get(url)
    if "Text" in data["Titel"]:
        folder = "Text"
    elif data["Titel"] == "Schreiben des RR":
        folder = "Antwort"
    else:
        folder = "Diverses"
    try:
        with open(
                f"/home/me/PycharmProjects/Grosser-Rat-Wrapper/pdfs/{folder}/{data['Doknummer'].replace('.', '_')}.pdf",
                'wb') as f:
            f.write(response.content)
    except AttributeError:
        print(data["Doknummer"])


def tag_pdf(data):
    if "Text" in data["Titel"]:
        folder = "Text"
    elif data["Titel"] == "Schreiben des RR":
        folder = "Antwort"
    else:
        folder = "Diverses"
    try:
        trailer = PdfReader(
            f"/home/me/PycharmProjects/Grosser-Rat-Wrapper/pdfs/{folder}/{data['Doknummer'].replace('.', '_')}.pdf")
        trailer.Info.Author = "Eric Weber"
        trailer.Info.Title = data["Geschäftstitel"]
        trailer.Info.Subject = data["Titel"]
        trailer.Info.DokNR = data['Doknummer']
        trailer.Info.Creator = ""
        trailer.Info.Producer = ""
        trailer.Info.Keywords = data["Geschäftstyp"]
        trailer.Info.Date = data.Datum.strftime("%d.%m.%Y")
        PdfWriter(
            f"/home/me/PycharmProjects/Grosser-Rat-Wrapper/pdfs/{folder}/{data['Doknummer'].replace('.', '_')}.pdf",
            trailer=trailer).write()
    except AttributeError:
        print(data["Doknummer"])
        pass


# def tag_pdf():
#     # Add tags to pdf
#     trailer = PdfReader("/tmp/test.pdf")
#     trailer.Info.Author = "Eric Weber"
#     trailer.Info.Title = combi["Geschäftstitel"].iloc[0]
#     trailer.Info.Subject = combi["Titel"].iloc[0]
#     trailer.Info.DokNR = combi["Doknummer"].iloc[0]
#     trailer.Info.Creator = ""
#     trailer.Info.Producer = ""
#     trailer.Info.Keywords = combi["Geschäftstyp"].iloc[0]
#     trailer.Info.Date = combi.Datum.iloc[0].strftime("%d.%m.%Y")
#     PdfWriter("/tmp/test.pdf", trailer=trailer).write()
pageResp = get_member_page('15003908')
gsnrList, linkList = create_linklist(pageResp)

gesHtmlList = asyncio.run(get_dok_details(linkList))
extract_ges_dok_info_2(gesHtmlList)
# with open(Path("/home/me/PycharmProjects/Grosser-Rat-Wrapper/dok_detail_list.pkl"), "wb") as f:
#     pickle.dump(ges_html_list, f)
with open(Path("/home/me/PycharmProjects/Grosser-Rat-Wrapper/dok_detail_list.pkl"), "rb") as f:
    ges_html_list = pickle.load(f)

for idx, row in combi.iterrows():
    # print(row)
    download_pdf(data=row)

for idx, row in combi.iterrows():
    # print(row)
    tag_pdf(data=row)
