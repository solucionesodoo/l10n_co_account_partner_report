# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    Autor: Brayhan Andres Jaramillo Castaño
#    Correo: brayhanjaramillo@hotmail.com
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

{
	"name": "Account Partner Report",
	"author": "Brayhan Andres Jaramillo Castaño",
	"version": "12.0",
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
