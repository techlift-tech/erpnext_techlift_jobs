# -*- coding: utf-8 -*-
# Copyright (c) 2021, Techlift and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from requests.sessions import session
from frappe.model.document import Document
import requests
import json
import urllib.parse
from bs4 import BeautifulSoup


class ERPNextJobsSettings(Document):
    pass

@frappe.whitelist()
def erpnext_jobs_sync():
    # Get settings doctype
    erpnext_jobs_settings = frappe.get_doc("ERPNext Jobs Settings")
    if not erpnext_jobs_settings:
        return

    # Get username, password and url from the settings doctype
    username = erpnext_jobs_settings.username
    password = erpnext_jobs_settings.get_password("password")
    url = erpnext_jobs_settings.url
    jobs_url = erpnext_jobs_settings.jobs_url
    job_contact_url = erpnext_jobs_settings.job_contact_url
    company = erpnext_jobs_settings.company

    if not (username and password and url and jobs_url and job_contact_url and company):
        frappe.msgprint("Check ERPNext Job Settings")
        return

    # Login and return the session for further calls
    session = __erpnext_login_and_return_session(
        username, password, url + "/api/method/login"
    )
    if not session:
        frappe.msgprint("Unable to create Session")
        return

    # Get Job pade HTML
    response = session.get(url=jobs_url)
    total_added = 0
    if response.ok:
        job_link_wise_data = {}
        job_links = __get_job_links_from_html(response.text)
        frappe.msgprint("Found %s job links"%len(job_links))
        
        for job_link in job_links:
            job_data_response = session.get(job_contact_url + "/" + job_link)
            if job_data_response.ok:
                job_data = __get_data_from_job_page(job_data_response.text)
                added_new = __create_lead_if_does_not_exist(job_contact_url + "/" + job_link, job_data, company)
                if added_new:
                    total_added = total_added + 1

    frappe.msgprint("Added %s New Jobs"%(total_added))


def __erpnext_login_and_return_session(username, password, url):
    session = requests.session()
    headers = {"Content-type": "application/json"}
    payload = {"usr": username, "pwd": password}

    payload_string = json.dumps(payload)
    respose = session.request("POST", url=url, headers=headers, data=payload_string)

    if respose.ok:
        return session
    else:
        return False


def __get_job_page_html(session, base_url):
    return session.get(base_url + "/erpnext-jobs")


def __get_job_links_from_html(html_text):
    href_to_return = []
    soup = BeautifulSoup(html_text, "html.parser")
    anchors = soup.find_all("a", class_="card mb-4", href=True)
    for anchor in anchors:
        href_to_return.append(anchor["href"])

    return href_to_return


def __get_data_from_job_page(html_text):
    data_to_return = {}
    soup = BeautifulSoup(html_text, "html.parser")
    tables = soup.find_all("table")
    title_h1 = soup.find_all("h1")
    h3_tags = soup.find_all("h3")

    for h3_tag in h3_tags:
        h3_tag_text = h3_tag.get_text()
        if h3_tag_text == "Details":
            next_p = h3_tag.find_next("p")
            details_text = next_p.get_text()
            data_to_return["details"] = details_text
            break

    if len(title_h1) == 1:
        data_to_return["title"] = title_h1[0].get_text()

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            columns = row.find_all("td")
            if len(columns) != 2:
                continue
            prop = columns[0].get_text()
            value = columns[1].get_text()
            data_to_return[prop] = value
    return data_to_return

def __create_lead_if_does_not_exist(job_link, job_data, company):
    email_id = job_data["Email"]
    lead_exist = frappe.get_all("Lead", filters={"email_id": email_id})
    title = job_data["title"]
    details = job_data["details"]
    job_type = job_data["Job Type"]

    if len(lead_exist) == 0:
        doc = frappe.get_doc({
            'doctype': 'Lead',
            'source':  'ERPNext Jobs',
            'email_id': job_data['Email'],
            'mobile_no': job_data['Phone (optional)'],
            'phone': job_data['Phone (optional)'],
            'lead_name': job_data['Company Name'],
        })
        doc.save()
        frappe.db.commit()
        added_new = __add_oppurtunity_if_not_exist(job_link, doc.name, company, title, details, job_type)
    else:
        lead_name = lead_exist[0].name
        added_new = __add_oppurtunity_if_not_exist(job_link, lead_name, company, title, details, job_type)

    return added_new
def __add_oppurtunity_if_not_exist(job_link, lead_name, company, title, details, job_type):
    job_link_html = '<a href="%s">Job Url</a>'%(job_link)
    opp_exist = frappe.get_all("Opportunity", filters={"lead_url_store": job_link_html})
    print(job_link_html)
    if len(opp_exist) == 0:
        doc = frappe.get_doc({
            "doctype": "Opportunity",
            "opportunity_from": "Lead",
            "party_name": lead_name,
            "lead_url_store": job_link_html,
            "company": company,
            "source": "ERPNext Jobs",
            "erpnext_job_title": title,
            "details": details,
            "job_type": job_type
        })
        doc.save()
        frappe.db.commit()
        return True
    else:
        return False

def add_lead_source_if_does_not_exist():
    try:
        erpnext_lead_source = frappe.get_doc("Lead Source", "ERPNext Jobs")
    except:
        erpnext_lead_source = frappe.get_doc({
            "doctype": "Lead Source",
            "source_name": "ERPNext Jobs"
        })
        erpnext_lead_source.save()
    
