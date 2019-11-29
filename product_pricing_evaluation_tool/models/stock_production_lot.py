# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# -*- coding: utf-8 -*-
import time
import xlwt
import base64
import re
import io
import calendar
from io import StringIO
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class StockProductionLotEvaluation(models.Model):
    _inherit = 'stock.production.lot'

    standard_price = fields.Float('standard_price', related='product_id.standard_price')

    state_pe = fields.Selection([('new', 'New'),
                              ('factory', 'Factory'),
                              ('bought', 'Bought'),
                              ('sold', 'Sold'),
                              ('installed', 'Installed')], 'State PE', required=True,
                             track_visibility='onchange',
                                default='new')

    factory_paid = fields.Selection([('Y', 'Y'),
                                     ('N', 'N')], 'Factory Paid', default='N',
    compute = '_calcular_factory_paid')

    @api.one
    def _calcular_factory_paid(self):
        id_product = self.product_id.id
        obj_invoice = self.env['account.invoice.line'].search([('product_id', '=', id_product)])
        if obj_invoice:
            for id in obj_invoice:
                if id.invoice_id.state == 'paid':
                    self.factory_paid = 'Y'
                else:
                    self.factory_paid = 'N'
        else:
            self.factory_paid = 'N'



    serial_number_pt = fields.Char("Serial Number")

    calculation = fields.Boolean('Calculation')
    accessories_ids = fields.One2many('accessories.list', 'template_id', string='Accessories')
    commissions_ids = fields.One2many('commissions.list', 'template_id', string='Commissions')

    """====================="""
    less_warranty_discount_por = fields.Float('Less Warranty Discount %', digits=(10, 2))
    less_warranty_discount = fields.Float('Less Warranty Discount', digits=(10, 2), compute='_calcular_less_warranty')

    @api.one
    @api.depends('less_warranty_discount_por', 'standard_price')
    def _calcular_less_warranty(self):
        if (self.less_warranty_discount_por * self.product_id.standard_price) != 0:
            self.less_warranty_discount = self.less_warranty_discount_por * self.product_id.standard_price / 100
    """====================="""



    exchange_rate_por = fields.Float('Exchange Rate %', digits=(10, 2), default=1.17)
    exchange_rate = fields.Float('Exchange Rate', digits=(10, 2), compute='_calcular_exchange_rate')

    @api.one
    @api.depends('exchange_rate_por', 'standard_price')
    def _calcular_exchange_rate(self):
        suma = self.product_id.standard_price - self.less_warranty_discount
        suma_ma = suma * self.exchange_rate_por
        self.exchange_rate = suma_ma - self.product_id.standard_price



    unit_price = fields.Float('Unit Price', digits=(10, 2), compute='_calcular_usd_price')

    olist_price = fields.Float('Unit Price', digits=(10, 2), track_visibility='always')

    authorize_price = fields.Boolean('Authorize Price', track_visibility='always')

    @api.onchange('authorize_price')
    def onchange_authorize_price(self):
        if self.authorize_price:
            print(self.olist_price)

            record_ids = self.env['product.template'].search([('id', '=', self.product_id.id)])
            for record in record_ids:
                record.write({'list_price': self.olist_price,})

    @api.one
    @api.depends('standard_price', 'exchange_rate', 'less_warranty_discount')
    def _calcular_usd_price(self):
        self.unit_price = self.product_id.standard_price - self.less_warranty_discount + self.exchange_rate

    freight_in_us = fields.Float('Freight In US', digits=(10, 2))


    total_fob = fields.Float('Total Fob', digits=(10, 2), compute='_calcular_fob')

    @api.one
    @api.depends('freight_in_us', 'unit_price')
    def _calcular_fob(self):
        self.total_fob = self.freight_in_us + self.unit_price


    total_cost_delivered = fields.Float('Total Unit Cost as Delivered Sum', digits=(10, 2), compute='_calc_total_cost_delivered')
    @api.one
    @api.depends('accessories_ids','total_fob')
    def _calc_total_cost_delivered(self):
        tacc = 0
        if self.accessories_ids:
            for acc in self.accessories_ids:
                if acc.price > 0:
                    tacc += acc.price
            self.total_cost_delivered = tacc

    total_cost_delivered_t = fields.Float('Total Unit Cost as Delivered', digits=(10, 2),
                                        compute='_calc_total_cost_delivered_t')

    @api.one
    @api.depends('total_cost_delivered','unit_price')
    def _calc_total_cost_delivered_t(self):
        self.total_cost_delivered_t = self.total_cost_delivered + self.total_fob


    total_commission = fields.Float('commission', digits=(10, 2), compute='_calc_total_commission')
    @api.one
    @api.depends('commissions_ids')
    def _calc_total_commission(self):
        tacc = 0
        if self.commissions_ids:
            for com in self.commissions_ids:
                if com.commission > 0:
                    tacc += com.commission
            self.total_commission = tacc





    freight_to_customer = fields.Float('Freight to Customer', digits=(10, 2))

    warranty = fields.Float('Warranty', digits=(10, 2))
    bk = fields.Float('Pre Delivery', digits=(10, 2))



    floor_por = fields.Float('Financing/Floor Plan %', digits=(10, 2))
    floor_rate = fields.Float('Financing/Floor Plan', digits=(10, 2), compute='_calc_floor_rate')
    @api.one
    @api.depends('floor_por','total_cost_delivered_t')
    def _calc_floor_rate(self):
        self.floor_rate = self.floor_por/100 * self.olist_price

    dime_bank_interest_charges = fields.Float('Dime Bank Interest Charges', digits=(10, 2), compute='_calc_day_bank_interest')
    @api.one
    @api.depends('per_day', 'days_financed')
    def _calc_day_bank_interest(self):
        self.dime_bank_interest_charges = self.per_day * self.days_financed

    sub_total = fields.Float('Sub Total', digits=(10, 2), compute='_calc_sub_total')

    @api.one
    @api.depends('total_cost_delivered_t', 'freight_to_customer','warranty','bk','total_commission','floor_rate','dime_bank_interest_charges')
    def _calc_sub_total(self):
        self.sub_total = self.total_cost_delivered_t + self.freight_to_customer  + self.warranty + self.bk + self.total_commission + self.floor_rate

    risk_factor = fields.Float('Risk Factor %', digits=(10, 2))
    risk_factor_value = fields.Float('Risk Factor', digits=(10, 2), compute='_calc_risk_factor_value')

    @api.one
    @api.depends('risk_factor', 'sub_total')
    def _calc_risk_factor_value(self):
        if (self.sub_total) != 0:
            self.risk_factor_value = self.risk_factor/100 * self.sub_total

    cogs = fields.Float('Total COGS', digits=(10, 2), compute='_calc_cogs')
    @api.one
    @api.depends('risk_factor_value', 'sub_total')
    def _calc_cogs(self):
        self.cogs = self.risk_factor_value + self.sub_total

    over_factor = fields.Float('Overhead Factor Applied Factor %', digits=(10, 2))
    over_factor_total = fields.Float('Overhead Factor Applied', digits=(10, 2), compute='_calc_over_factor_total')

    @api.one
    @api.depends('over_factor', 'cogs')
    def _calc_over_factor_total(self):
        self.over_factor_total = self.over_factor * self.total_cost_delivered_t


    total_costs = fields.Float('Total Costs', digits=(10, 2), compute='_calc_total_costs')

    @api.one
    @api.depends('cogs', 'over_factor_total','freight_in_us')
    def _calc_total_costs(self):
        self.total_costs = self.cogs + self.over_factor_total

    net_profit = fields.Float('Net Profit (with OH)', digits=(10, 2), compute='_calc_net_profit')
    net_profit_por = fields.Float('Net Profit (with OH) %', digits=(10, 2), compute='_calc_net_profit')
    @api.one
    @api.depends('total_costs', 'olist_price')
    def _calc_net_profit(self):
        self.net_profit = self.olist_price - self.total_costs
        if (self.olist_price) != 0:
            self.net_profit_por = self.net_profit / self.olist_price * 100





    gross_profit = fields.Float('Gross Profit without OH)', digits=(10, 2) , compute='_calc_gross_profit')
    gross_profit_por = fields.Float('Gross Profit without OH) %', digits=(10, 2), compute='_calc_gross_profit')

    @api.one
    @api.depends('cogs', 'olist_price')
    def _calc_gross_profit(self):
        self.gross_profit = self.olist_price - self.cogs
        if (self.olist_price) != 0:
            self.gross_profit_por = self.gross_profit / self.olist_price * 100


    price_target_marg_por = fields.Float('Price at Target Margin %', digits=(10, 2), default=10)
    price_target_marg = fields.Float('Price at Target Margin', digits=(10, 2), default=10, compute='_calc_price_target_marg')

    @api.one
    @api.depends('total_costs', 'price_target_marg_por','freight_in_us')
    def _calc_price_target_marg(self):
        if (self.price_target_marg_por) != 0:
            self.price_target_marg = self.total_costs / (1-self.price_target_marg_por/100)



    days_financed = fields.Float('Days Financed', digits=(10, 2), default=10)
    interest_rate = fields.Float('Interest Rate', digits=(10, 2), default=10)
    per_day = fields.Float('per Day', digits=(10, 2), compute='_calc_per_day')

    @api.one
    @api.depends('unit_price','interest_rate','days_financed')
    def _calc_per_day(self):
        self.per_day = (self.unit_price * self.interest_rate/100)/360

    day_bank_interest = fields.Float('Dime Bank Interest to Date', digits=(10, 2), default=10, compute='_cal_day_bank_interest')

    @api.one
    @api.depends('days_financed', 'per_day')
    def _cal_day_bank_interest(self):
        self.day_bank_interest = self.days_financed * self.per_day

    attachment_list_ids = fields.Many2many('ir.attachment', string='Attachment List')

    @api.multi
    def button_print_xls(self):
        self.ensure_one
        today = datetime.today().strftime("%d-%m-%Y")
        workbook = xlwt.Workbook(encoding="utf-8")

    def print_excel(self):
        record_ids = self._context.get('active_ids')

        if not record_ids:
            raise UserError('There are no selected products.')
        """
        abstract_model = self.env['report.l10n_cl_base.report_8column_balance']
        asset_type_ids = fr_obj.browse(self.asset_fr_id.id).account_type_ids.ids
        liability_type_ids = fr_obj.browse(self.liability_fr_id.id).account_type_ids.ids
        income_type_ids = fr_obj.browse(self.income_fr_id.id).account_type_ids.ids
        expense_type_ids = fr_obj.browse(self.expense_fr_id.id).account_type_ids.ids
        types = asset_type_ids + liability_type_ids + income_type_ids + expense_type_ids
        accounts = self.env['account.account'].search([('user_type_id', 'in', types)])
        account_res = abstract_model._get_accounts(accounts, self.read([])[0])
        summatory = abstract_model._get_summatory(account_res)
        difference = abstract_model._get_difference(summatory)
        totals = abstract_model._get_totals(summatory, difference)
        """
        workbook = xlwt.Workbook(encoding="utf-8")
        header_style2 = xlwt.easyxf(
            'pattern: pattern solid, pattern_fore_colour pale_blue, pattern_back_colour gray25; font: bold on, height 160; align: wrap on, horiz center, vert center;')
        date_style = xlwt.easyxf(num_format_str='D/M/YY')
        datetime_style = xlwt.easyxf('font: height 140; align: wrap yes', num_format_str='YYYY-MM-DD HH:mm:SS')
        today = datetime.today().strftime("%d-%m-%Y")
        worksheet = workbook.add_sheet('Product Report')
        col = 0
        worksheet.write_merge(0, 1, 0, 0, 'Item', header_style2)
        worksheet.write_merge(0, 1, 1, 1, 'Description', header_style2)
        worksheet.write_merge(0, 1, 2, 2, 'Purchase Date', header_style2)
        worksheet.write_merge(0, 1, 3, 3, 'Location of Fixed Asset', header_style2)
        worksheet.write_merge(0, 1, 4, 4, 'Euro Value', header_style2)
        worksheet.write_merge(0, 1, 5, 5, 'Conversion Rate', header_style2)
        worksheet.write_merge(0, 1, 6, 6, 'Cost USD', header_style2)
        worksheet.write_merge(0, 1, 7, 7, 'Freight', header_style2)
        worksheet.write_merge(0, 1, 8, 8, 'Total Fob', header_style2)
        worksheet.write_merge(0, 1, 9, 9, 'Factory Paid', header_style2)
        worksheet.write_merge(0, 1, 10, 10, 'Attachments', header_style2)
        worksheet.write_merge(0, 1, 11, 11, 'Additional transports Cost', header_style2)
        worksheet.write_merge(0, 1, 12, 12, 'Warranty', header_style2)
        worksheet.write_merge(0, 1, 13, 13, 'Prep Labor', header_style2)
        worksheet.write_merge(0, 1, 14, 14, 'Other cost', header_style2)
        worksheet.write_merge(0, 1, 15, 15, 'Commission', header_style2)
        worksheet.write_merge(0, 1, 16, 16, 'Financial Floor Plan', header_style2)
        worksheet.write_merge(0, 1, 17, 17, 'Dime Bank', header_style2)
        worksheet.write_merge(0, 1, 18, 18, 'Subtotal', header_style2)
        worksheet.write_merge(0, 1, 19, 19, 'OH Factor', header_style2)
        worksheet.write_merge(0, 1, 20, 20, 'Total Cost', header_style2)
        worksheet.write_merge(0, 1, 21, 21, 'Invoice Amount w/Shipping', header_style2)
        worksheet.write_merge(0, 1, 22, 22, 'Sold to', header_style2)
        worksheet.write_merge(0, 1, 23, 23, 'Date Sold', header_style2)
        worksheet.write_merge(0, 1, 24, 24, 'Rcvd Pymnt', header_style2)
        worksheet.write_merge(0, 1, 25, 25, 'Gross Profit w/o Overhead', header_style2)
        worksheet.write_merge(0, 1, 26, 26, 'Net Profit', header_style2)
        row_index = 2
        col = 0
        myrow = 0


        cont = 2
        for product in self.env['stock.production.lot'].browse(record_ids):
            cont += 1
            if product.calculation:
                """ Buscamos la Ubicación """
                locattion = "-"
                obj_stock_move_line = self.env['stock.move.line'].search([('lot_id', '=', product.id)], limit=1)
                for id in obj_stock_move_line:
                    if id.location_dest_id.name:
                        locattion = id.location_dest_id.name

                j = 0
                worksheet.write(row_index, j, str(product.name), ); j += 1
                worksheet.write(row_index, j, str(product.product_id.name), ); j += 1
                worksheet.write(row_index, j, product.purchase_date, date_style); j += 1
                worksheet.write(row_index, j, locattion, ); j += 1
                worksheet.write(row_index, j, product.product_id.standard_price, ); j += 1
                worksheet.write(row_index, j, product.exchange_rate_por, ); j += 1
                worksheet.write(row_index, j, product.unit_price, ); j += 1
                worksheet.write(row_index, j, product.freight_in_us, ); j += 1
                worksheet.write(row_index, j, product.total_fob, ); j += 1
                worksheet.write(row_index, j, product.factory_paid, ); j += 1

                worksheet.write(row_index, j, 0, );j += 1
                worksheet.write(row_index, j, product.total_cost_delivered, ); j += 1
                worksheet.write(row_index, j, product.warranty, ); j += 1
                worksheet.write(row_index, j, product.bk, ); j += 1
                worksheet.write(row_index, j, 0, ); j += 1
                worksheet.write(row_index, j, product.total_commission, ); j += 1
                worksheet.write(row_index, j, product.floor_rate, );j += 1
                worksheet.write(row_index, j, product.dime_bank_interest_charges, );j += 1

                subtotal_form = product.total_cost_delivered + product.warranty + product.bk + product.total_commission + product.floor_rate + product.dime_bank_interest_charges

                worksheet.write(row_index, j, subtotal_form, );j += 1
                worksheet.write(row_index, j, product.over_factor_total, ); j += 1

                total_cost = product.over_factor_total + product.sub_total

                worksheet.write(row_index, j, total_cost, ); j += 1
                worksheet.write(row_index, j, 0, ); j += 1
                worksheet.write(row_index, j, product.sold_id.name, ); j += 1
                worksheet.write(row_index, j, product.date_sold, date_style); j += 1
                worksheet.write(row_index, j, product.rcvd_pymnt, date_style); j += 1
                worksheet.write(row_index, j, product.gross_profit, ); j += 1
                worksheet.write(row_index, j, product.net_profit,);j += 1
                row_index += 1


        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        data_b64 = base64.encodestring(data)
        attach = self.env['ir.attachment'].create({
            'name': '%s %s.xls' % ('Product_Report_1000', today),
            'type': 'binary',
            'datas': data_b64,
            'datas_fname': '%s %s.xls' % ('Product_Report_1000', today),
        })
        return {
            'type': "ir.actions.act_url",
            'url': "web/content/?model=ir.attachment&id=" + str(
                attach.id) + "&filename_field=datas_fname&field=datas&download=true&filename=" + str(attach.name),
            'target': "self",
            'no_destroy': False,
        }

    purchase_date = fields.Date('Purchase Date', track_visibility='onchange')
    date_sold = fields.Date('Date Sold', track_visibility='onchange')
    rcvd_pymnt = fields.Date('Rcvd Pymnt', track_visibility='onchange')
    sold_id = fields.Many2one('res.users', string='Sold to', track_visibility='onchange')






class CommissionsList(models.Model):
    _name = 'commissions.list'
    _description = 'Commissions List'
    employee_id = fields.Many2one('hr.employee', 'Employee')
    porcent = fields.Float()
    commission = fields.Float()
    note = fields.Char('Note')
    template_id = fields.Many2one('stock.production.lot', 'producto', ondelete='cascade')


class AccessoriesList(models.Model):
    _name = 'accessories.list'
    _description = 'Accessories List'
    product_id = fields.Many2one('product.product', 'Product')
    qty = fields.Float('Quantity')
    price = fields.Float()
    subtotal = fields.Float('Subtotal', compute='give_subtotal')
    note = fields.Char('Note')
    serial_number_pt = fields.Char("Serial Number", related='template_id.serial_number_pt')

    @api.one
    @api.depends('price','price')
    def give_subtotal(self):
        self.subtotal = self.qty * self.price

    @api.onchange('qty','price')
    def onchange_subtotal(self):
        self.subtotal = self.qty * self.price

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.price = self.product_id.standard_price

    template_id = fields.Many2one('stock.production.lot', 'producto', ondelete='cascade')


class AttachmentList(models.Model):
    _name = 'attachment.list'
    _description = "Attachment List"


    data = fields.Binary(string="Attachment", help='Attachment 01')
    data_filename = fields.Char("Attachment")



    date = fields.Datetime('Date', default=fields.Datetime.now)


    user_id = fields.Many2one('res.users', string='User', track_visibility='onchange',
                              default=lambda self: self.env.user)

    product_id = fields.Many2one('stock.production.lot', string="Attachment", ondelete='cascade')