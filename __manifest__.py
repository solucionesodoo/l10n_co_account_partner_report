# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) Brayhan Jaramillo.
#               brayhanjaramillo@hotmail.com


{
	"name": "Account Partner Report",
	"author": "Brayhan Andres Jaramillo Castaño",
	"version": "10.0",
	"summary": "",
	"category": "Report",
	'description': """

		Modificación a los reportes: \n

		Este modulo permite agregar un check en los reportes de contabilidad, donde se incluira el partner en las cuentas que tienen saldo,
		como también una opción para descargar un archivo Excel en los informes de Contabilidad
		
	""",
	"depends": ['account', 'base', 'l10n_co_res_partner'],
	"data": [

		'views/account_report_trialbalance_inherit.xml',
		'views/report_invoice_document_inherit.xml',
		'views/report_financial_inherit.xml'

	],

    "license": 'LGPL-3',
	'installable': True
}
