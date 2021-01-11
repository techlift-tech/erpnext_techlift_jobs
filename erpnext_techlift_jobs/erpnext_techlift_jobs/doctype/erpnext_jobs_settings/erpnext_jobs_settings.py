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
    if not (username and password and url and jobs_url and job_contact_url):
        return

    # Login and return the session for further calls
    session = __erpnext_login_and_return_session(
        username, password, url + "/api/method/login"
    )
    if not session:
        return

    # Get Job pade HTML
    response = session.get(url=jobs_url)
    if response.ok:
        job_link_wise_data = {}
        job_links = __get_job_links_from_html(response.text)
        for job_link in job_links:
            job_data_response = session.get(job_contact_url + "/" + job_link)
            if job_data_response.ok:
                job_data = __get_data_from_job_page(job_data_response.text)
                job_link_wise_data[job_link] = job_data


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

def __create_lead_if_does_not_exist(job_link, job_data):
    lead_exist = frappe.get_all("Lead", filters={"lead_url": job_link})
    if len(lead_exist) == 0:
        doc = frappe.get_doc({
            'doctype': 'Lead',
            'source':  'ERPNext Jobs',
            'email_id': job_data['Email'],
            'lead_url': job_link,
            'notes': '',
            'mobile_no': job_data['Phone (optional)'],
            'organization_lead': 1,
            'company_name': job_data['Company Name'],
            'job_type': job_data['Job Type'],
        })
        doc.save()
