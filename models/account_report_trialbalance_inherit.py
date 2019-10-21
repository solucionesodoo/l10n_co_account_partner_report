# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) Brayhan Jaramillo.
#               brayhanjaramillo@hotmail.com

import logging
from odoo import api, fields, models, _
_logger = logging.getLogger(__name__)

import xlsxwriter
from cStringIO import StringIO
import base64

import time
from datetime import datetime, timedelta, date
import sys
reload(sys)

sys.setdefaultencoding("utf-8")



class AccountingReportInherit(models.TransientModel):
	_inherit = "accounting.report"


	display_account = fields.Selection([('all','All'), ('movement','With movements'), 
										('not_zero','With balance is not equal to 0'), 
										('with_partner','¿Incluir Partner?')], 
										string='Display Accounts', required=True, default='movement')

	decimal_precision = fields.Boolean(u'Agregar Precisión Decimal')

	@api.multi
	def pre_print_report(self, data):
		data['form'].update(self.read(['display_account'])[0])
		return data

AccountingReportInherit()

class AccountCommonAccountReport(models.TransientModel):
	_inherit = 'account.common.account.report'

	
	display_account = fields.Selection([('all','All'), ('movement','With movements'), 
										('not_zero','With balance is not equal to 0'), 
										('with_partner','¿Incluir Partner?')], 
										string='Display Accounts', required=True, default='movement')


	@api.multi
	def pre_print_report(self, data):
		data['form'].update(self.read(['display_account'])[0])
		return data

AccountCommonAccountReport()



class ReportTrialBalanceInherit(models.AbstractModel):
	_inherit = 'report.account.report_trialbalance'

	"""
		Moficiacion de reporte y agregar un campo para sacar el partner en las cuentas
	"""
	
	def _get_accounts(self, accounts, display_account):


		account_result = {}
		# Prepare sql query base on selected parameters from wizard
		tables, where_clause, where_params = self.env['account.move.line']._query_get()
		tables = tables.replace('"','')
		if not tables:
			tables = 'account_move_line'
		wheres = [""]
		if where_clause.strip():
			wheres.append(where_clause.strip())
		filters = " AND ".join(wheres)
		# compute the balance, debit and credit for the provided accounts
		request = ("SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" +\
				   " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
		params = (tuple(accounts.ids),) + tuple(where_params)
		self.env.cr.execute(request, params)
		for row in self.env.cr.dictfetchall():
			account_result[row.pop('id')] = row

		account_res = []
		for account in accounts:
			res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
			currency = account.currency_id and account.currency_id or account.company_id.currency_id
			res['code'] = account.code
			res['name'] = account.name
			res['with_partner'] = False
			res['account_id'] = account.id
			if account.id in account_result.keys():
				res['debit'] = account_result[account.id].get('debit')
				res['credit'] = account_result[account.id].get('credit')
				res['balance'] = account_result[account.id].get('balance')
				
			if display_account == 'all':
				account_res.append(res)
			if display_account == 'not_zero' and not currency.is_zero(res['balance']):
				account_res.append(res)
			if display_account == 'movement' and (not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
				account_res.append(res)
			if display_account == 'with_partner' and not currency.is_zero(res['balance']):
				res['with_partner'] = True
				account_res.append(res)

		_logger.info('estamos desde el _get_accounts')
		_logger.info(account_res)
		return account_res

	def return_vals(self, name, code, credit, debit, balance, with_partner):

		vals={'code':code,
				'name':name,
				'credit':credit,
				'debit':debit,
				'balance':balance,
				'with_partner': with_partner}

		return vals


	def return_data_with_partner(self, account_res):

		model_account_move_line= self.env['account.move.line']
		data_account_res=[]


		for x in account_res:
			if x['with_partner']:

				group_data_move_line = model_account_move_line.sudo().read_group([('account_id', '=', x['account_id'])], 
					fields = [u'debit',u'credit', u'balance', u'name', 'account_id', 'partner_id',], 
					groupby = [u'account_id',u'partner_id'], orderby = 'account_id asc', lazy = False)

				
				data_account_res.append(self.return_vals(x['name'], x['code'], x['credit'], x['debit'], x['balance'], False))

				if group_data_move_line:
					for record in group_data_move_line:

						data_account_res.append(self.return_vals(record['partner_id'][1], self.env['res.partner'].search([('id', '=', record['partner_id'][0])]).xidentification, record['credit'], record['debit'], record['balance'], True))
			else:

				data_account_res=account_res

		return data_account_res

	@api.model
	def render_html(self, docids, data=None):
		if not data.get('form') or not self.env.context.get('active_model'):
			raise UserError(_("Form content is missing, this report cannot be printed."))

		self.model = self.env.context.get('active_model')
		docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
		display_account = data['form'].get('display_account')
		accounts = docs if self.model == 'account.account' else self.env['account.account'].search([])
		account_res = self.with_context(data['form'].get('used_context'))._get_accounts(accounts, display_account)


		data_account_res= self.return_data_with_partner(account_res)

		docargs = {
			'doc_ids': self.ids,
			'doc_model': self.model,
			'data': data['form'],
			'docs': docs,
			'time': time,
			'Accounts': data_account_res,
		}

		self.env['report.account.report_financial'].generate_excel(docargs, "Balance de Comprobacion", data_account_res, True)

		return self.env['report'].render('account.report_trialbalance', docargs)

ReportTrialBalanceInherit()