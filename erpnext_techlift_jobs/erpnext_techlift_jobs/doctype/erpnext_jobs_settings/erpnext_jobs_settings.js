// Copyright (c) 2021, Techlift and contributors
// For license information, please see license.txt

frappe.ui.form.on('ERPNext Jobs Settings', {
	sync_jobs_now: function (frm) {
		frappe.dom.freeze("Syncing Jobs Now")
		frappe.call({
			method: "erpnext_techlift_jobs.erpnext_techlift_jobs.doctype.erpnext_jobs_settings.erpnext_jobs_settings.erpnext_jobs_sync",
			args: {},
			callback: function(){
				frappe.dom.unfreeze()
			}
		})	
	}
});
