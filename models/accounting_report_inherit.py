# -*- coding: utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) Brayhan Jaramillo.
#               brayhanjaramillo@hotmail.com


# -*- coding: utf-8 -*-
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


from odoo.exceptions import UserError, RedirectWarning, ValidationError

class AccountCommonReportInherit(models.TransientModel):
	_inherit = 'account.common.report'

	filename = fields.Char('Filename')
	document = fields.Binary(string = 'Descargar Excel')

	
AccountCommonReportInherit()



class AccountingReportInherit(models.TransientModel):
	_inherit = "accounting.report"


	display_account = fields.Selection([('all','Todo'), 
		('movement','Con Movimientos'), 
		('not_zero','Con balance no es igual a 0'), 
		('with_partner','¿Incluir Partner?'),], 
		string='Mostrar Cuentas', required=True, default='movement')
	print_excel = fields.Boolean('¿Imprimir Excel?')

	
	@api.multi
	def pre_print_report(self, data):
		data['form'].update(self.read(['display_account'])[0])
		data['form'].update(self.read(['print_excel'])[0])
		return data

	@api.multi
	def print_report_excel(self):
		_logger.info('hola')

		self.display_account = 'with_partner'
	@api.multi
	def check_report(self):

		res = super(AccountingReportInherit, self).check_report()
		data = {}
		data['form'] = self.read(['account_report_id', 'date_from_cmp', 'date_to_cmp', 'journal_ids', 'filter_cmp', 'target_move', 'display_account', 'print_excel'])[0]
		for field in ['account_report_id']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		comparison_context = self._build_comparison_context(data)
		res['data']['form']['comparison_context'] = comparison_context

		return res

	def _print_report(self, data):
		data['form'].update(self.read(['date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter', 'target_move', 'display_account', 'print_excel'])[0])

		return self.env['report'].get_action(self, 'account.report_financial', data=data)


AccountingReportInherit()


class ReportFinancialInherit(models.AbstractModel):
	
	_inherit = "report.account.report_financial"




	def get_account_lines(self, data):
		lines = []
		account_report = self.env['account.financial.report'].search([('id', '=', data['account_report_id'][0])])
		child_reports = account_report._get_children_by_order()
		res = self.with_context(data.get('used_context'))._compute_report_balance(child_reports)
		if data['enable_filter']:
			comparison_res = self.with_context(data.get('comparison_context'))._compute_report_balance(child_reports)
			for report_id, value in comparison_res.items():
				res[report_id]['comp_bal'] = value['balance']
				report_acc = res[report_id].get('account')
				if report_acc:
					for account_id, val in comparison_res[report_id].get('account').items():
						report_acc[account_id]['comp_bal'] = val['balance']

		for report in child_reports:
			vals = {
				'name': report.name,

				'balance': res[report.id]['balance'] * report.sign,
				'type': 'report',
				'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
				'account_type': report.type or False, #used to underline the financial report balances
			}
			vals['with_partner']= False
			vals['print_excel']= False
			if data['display_account'] == 'with_partner':

				_logger.info('escogio partner')
				vals['with_partner']= True

			if data['print_excel']:
				vals['print_excel']= True

			if data['debit_credit']:
				vals['debit'] = res[report.id]['debit']
				vals['credit'] = res[report.id]['credit']
				vals['with_dc']= True

			if data['enable_filter']:
				vals['balance_cmp'] = res[report.id]['comp_bal'] * report.sign

		
			if report.display_detail == 'no_detail':
				#the rest of the loop is used to display the details of the financial report, so it's not needed here.
				continue

			if res[report.id].get('account'):
				sub_lines = []
				for account_id, value in res[report.id]['account'].items():
					#if there are accounts to display, we add them to the lines with a level equals to their level in
					#the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
					#financial reports for Assets, liabilities...)
					flag = False
					account = self.env['account.account'].browse(account_id)
					vals = {
						'name': account.code + ' ' + account.name,
						'account_id': account.id,
						'balance': value['balance'] * report.sign or 0.0,
						'type': 'account',
						'level': report.display_detail == 'detail_with_hierarchy' and 4,
						'account_type': account.internal_type,
					}
					vals['with_partner']= False
					vals['print_excel']= False
					if data['display_account'] == 'with_partner':
						_logger.info('escogio partner')
						vals['with_partner']= True

					if data['print_excel']:
						vals['print_excel']= True

					if data['debit_credit']:
						vals['debit'] = value['debit']
						vals['credit'] = value['credit']
						vals['with_dc']= True
						if not account.company_id.currency_id.is_zero(vals['debit']) or not account.company_id.currency_id.is_zero(vals['credit']):
							flag = True
					if not account.company_id.currency_id.is_zero(vals['balance']):
						flag = True
					if data['enable_filter']:
						vals['balance_cmp'] = value['comp_bal'] * report.sign
						if not account.company_id.currency_id.is_zero(vals['balance_cmp']):
							flag = True
					if flag:
						sub_lines.append(vals)
				lines += sorted(sub_lines, key=lambda sub_line: sub_line['name'])
	
		return lines

	def return_vals(self, name, credit, debit, balance, with_partner, account_type, level, type_account, account_id):


		vals={
				'name':name,
				'credit':credit,
				'debit':debit,
				'balance':balance,
				'with_partner': with_partner,
				'account_type': account_type,
				'level': level,
				'type': type_account,
				'account_id': account_id
				}

		return vals

	def return_data_with_partner(self, report_lines):

		model_account_move_line= self.env['account.move.line']
		data_report_lines=[]

		for x in report_lines:

			if x['with_partner']:

				if x['balance'] != 0:

					if 'account_id' in x:

						credit= 0
						debit= 0
					
						if ('debit' in x) and ('credit' in x):

							credit= x['credit']
							debit= x['debit']
					
						data_report_lines.append(self.return_vals(x['name'], credit, debit, x['balance'], False, x['account_type'], x['level'], x['type'], x['account_id']))


						group_data_move_line = model_account_move_line.sudo().read_group([('account_id', '=', x['account_id'])], fields = [u'debit',u'credit', u'balance', u'name', 'account_id', 'partner_id'], groupby = [u'account_id',u'partner_id'], orderby = 'account_id asc', lazy = False)

						if group_data_move_line:
							
							for record in group_data_move_line:
								identification= self.env['res.partner'].search([('id', '=', record['partner_id'][0])]).xidentification
								credit= 0
								debit= 0
								balance= record['balance']
								name= identification + ' ' + record['partner_id'][1]

								if ('debit' in x) and ('credit' in x):

									credit= record['credit']
									debit= record['debit']

								data_report_lines.append(self.return_vals(name, credit, debit, balance, True, x['account_type'], x['level'], x['type'], x['account_id']))

		return data_report_lines


	"""
		Esta funcion retorna el tipo de display_account que se ha seleccionado
	"""
	def return_string_display_account(self, display_account):

		return_string=""

		if display_account:

			if display_account == 'with_partner':
				return_string= "Cuentas con Tercero"
			if display_account == 'all':
				return_string= "Cuentas con Todo"
			if display_account == 'movement':
				return_string= "Cuentas con Movimientos"
			if display_account == 'not_zero':
				return_string= "Cuentas con Balance no es igual a 0"
			
		return return_string

	"""
		Esta funcion retorna el tipo de target_move que se ha seleccionado
	"""
	def return_target_move(self, target_move):

		return_string=""

		if target_move:
			if target_move == 'posted':
				return_string= "Todos los Asientos Validados"
			if target_move == 'all':
				return_string= "Todos los Asientos"

		return return_string

	"""
		Esta funcion permite validar si esta las fecha de inicio y fecha de fin
	"""
	def validate_date_data(self, data):

		flag=False
		if data:
			if data['date_to'] and data['date_from']:
				flag=True
		return flag

	"""
		Esta función permite retornar una data con ciertas validaciones
	"""
	def return_data_report(self, docargs, name_report, data_account, debit_credit):

		display_account=""
		target_move = ""
		validate_date = False
		date_from = False
		date_to = False
		data = []

		if docargs:

			display_account = self.return_string_display_account(docargs['data']['display_account'])
			target_move = self.return_target_move(docargs['data']['target_move'])
			validate_date = self.validate_date_data(docargs['data'])	

			
			if validate_date:
				date_to = docargs['data']['date_to']
				date_from = docargs['data']['date_from']

			vals={

				'name_report': name_report,
				'display_account': display_account,
				'target_move': target_move,
				'debit_credit': debit_credit,
				'data_account': data_account,
				'validate_date': validate_date,
				'date_to': date_to,
				'date_from': date_from,

				#name_report = docargs['data']['account_report_id'][1]
				#'data_account': docargs['get_account_lines']
			}

		return vals


	"""
		Esta funcion permite retornar los datos mas importantes de la compania
	"""
	def return_information_company(self):
		company_id = self.env.user.company_id
		name = company_id.name
		nit = company_id.partner_id.formatedNit
		street = company_id.street
		email = company_id.email
		city = company_id.partner_id.xcity.name
		state = company_id.partner_id.state_id.name
		city_state = state + ' ' + city
		country_id = company_id.country_id.name
		phone = company_id.phone
		website = company_id.website

		vals = {
			'name': name,
			'nit': 'Nit: ' +  nit,
			'street': street + ' ' + company_id.street2,
			'email': email,
			'city_state': city_state,
			'country_id': country_id,
			'phone': phone,
			'website': website
		}

		return vals

	@api.multi
	def generate_excel(self, docargs, name_report, data_account, debit_credit):

		data_report = self.return_data_report(docargs, name_report, data_account, debit_credit)
		data_company = self.return_information_company()


		name_report = str(data_report['name_report']).upper()

		Header_Text = name_report
		file_data = StringIO()
		workbook = xlsxwriter.Workbook(file_data)
		worksheet = workbook.add_worksheet(name_report)
		
		#Formato de letras y celdas
		bold = workbook.add_format({'bold': 1,'align':'left','border':1, 'font_size': 14})
		format_tittle = workbook.add_format({'bold': 1,'align':'center', 'valign':'vcenter', 'border':1, 'fg_color':'#F9CEA9', 'font_size': 25 })
		letter_gray_name = workbook.add_format({'align':'left', 'font_color': 'gray', 'indent':2, 'font_size': 14})
		letter_gray = workbook.add_format({'align':'right', 'font_color': 'gray', 'num_format': '$#,##0.00', 'font_size': 14})
		letter_black_name = workbook.add_format({'align':'left', 'font_color': 'black', 'num_format': '$#,##0.00', 'font_size': 14})
		letter_black = workbook.add_format({'align':'right', 'font_color': 'black', 'num_format': '$#,##0.00', 'font_size': 14})
		header_format = workbook.add_format({'bold': 1,'align':'center','valign':'vcenter', 'border':1, 'fg_color':'#F9CEA9', 'font_size': 18 })


		worksheet.set_column('A1:A1',35)
		worksheet.set_column('B1:B1',35)
		worksheet.set_column('C1:C1',35)
		worksheet.set_column('D1:C1',35)
		worksheet.set_column('E1:E1',35)
		worksheet.set_column('F1:F1',35)
		worksheet.set_column('G1:G1',35)
		worksheet.set_column('H1:H1',35)
		worksheet.set_column('J1:J1',35)
		worksheet.set_column('K1:K1',35)
		worksheet.set_column('L1:L1',35)

		preview = name_report 

		for i in range(1):
			worksheet.write('A1', data_company['name'], bold)
			if data_company['nit']:
				worksheet.write('A2', data_company['nit'], bold)
			if data_company['street']:
				worksheet.write('A3', data_company['street'], bold)
			if data_company['phone']:
				worksheet.write('A4', data_company['phone'], bold)
			if data_company['city_state']:
				worksheet.write('A5', data_company['city_state'], bold)
			if data_company['country_id']:
				worksheet.write('A6', data_company['country_id'], bold)
			if data_company['email']:
				worksheet.write('A7', data_company['email'], bold)
			if data_company['website']:
				worksheet.write('A7', data_company['website'], bold)

			worksheet.merge_range('C3:D4',preview, format_tittle)

			if data_report['target_move']:
				worksheet.write('A9', "Movimientos Senalados", header_format)
				worksheet.write('A10', data_report['target_move'], bold)


			if data_report['display_account']:
				worksheet.write('C9', "Cuentas", header_format)
				worksheet.write('C10', data_report['display_account'], bold)

			if data_report['validate_date']:
				worksheet.merge_range('E9:F9', "Rango de Fechas", header_format)
				worksheet.write('E10', "Fecha Inicial", bold)
				worksheet.write('F10', data_report['date_to'], bold)
				worksheet.write('E11', "Fecha Final", bold)
				worksheet.write('F11', data_report['date_from'], bold)

			format="%Y-%m-%d %H:%M:00"
			now=fields.Datetime.context_timestamp(self, fields.Datetime.from_string(fields.Datetime.now()))
			date_today=str(datetime.strftime(now, format))
			worksheet.write('F1', "Fecha Creacion", header_format)
			worksheet.write('F2', date_today, bold)

			if len(data_report['data_account']) > 0:

				worksheet.merge_range('A13:C13', "Nombre", header_format)

				if data_report['debit_credit']:
					worksheet.write('D13', 'Debito', header_format)
					worksheet.write('E13', 'Credito', header_format)
					worksheet.write('F13', 'Saldo Pendiente', header_format)
				else:
					worksheet.write('D13', 'Saldo Pendiente', header_format)

				row=13
				col=0

				for x in data_report['data_account']:
					cadena= unicode(x['name'].encode("utf8"))
					cadena= cadena.encode('utf-8')

					format_letter= letter_black

					if x['with_partner']:
						format_letter = letter_gray 
						worksheet.write(row,col, cadena or '', letter_gray_name)

					else:

						format_letter = letter_black
						worksheet.write(row,col, cadena or '', letter_black_name)

					if data_report['debit_credit']:

						worksheet.write(row,col+3 , x['debit'] or 0, format_letter)
						worksheet.write(row,col+4 , x['credit'] or 0, format_letter)
						worksheet.write(row,col+5 , x['balance'] or 0, format_letter)
			
					else:

						worksheet.write(row,col+3 , x['balance'] or 0, format_letter)
					
					row+=1


			workbook.close()
			file_data.seek(0)

		self_id= 0
		for x in docargs['docs']:
			_logger.info('holis')
			_logger.info(x.id)
			self_id= x.id
			x.write({'document':base64.encodestring(file_data.read()), 'filename':Header_Text+'.xlsx'})
			
	@api.model
	def render_html(self, docids, data=None):
		if not data.get('form') or not self.env.context.get('active_model') or not self.env.context.get('active_id'):
			raise UserError(_("Form content is missing, this report cannot be printed."))

		self.model = self.env.context.get('active_model')
		docs = self.env[self.model].browse(self.env.context.get('active_id'))
		report_lines = self.get_account_lines(data.get('form'))



		aux=[]
		for y in docs:
			if y['display_account'] == 'not_zero':
				for x in report_lines:
					if x['balance'] != 0:
						aux.append(x)

			elif y['display_account'] == 'with_partner':

				aux= self.return_data_with_partner(report_lines)

			else:
				aux=report_lines

		docargs = {
			'doc_ids': self.ids,
			'doc_model': self.model,
			'data': data['form'],
			'docs': docs,
			'time': time,
			'get_account_lines': aux,
		}

		_logger.info(docargs)
		self.generate_excel(docargs, docargs['data']['account_report_id'][1], docargs['get_account_lines'], docargs['data']['debit_credit'])

		return self.env['report'].render('account.report_financial', docargs)

ReportFinancialInherit()