# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from datetime import date

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
        
    invoice_number_eva = fields.Char(
        string='Invoice Number', default='0',
        help="Invoice Number", copy=False)

    @api.multi
    def action_invoice_open(self):
        ''' Herencia de metodo original de validacion de facturas.'''
        res = super(AccountInvoice, self).action_invoice_open()

        if not self.date:
            mydate = date.today()
        else:
            mydate = self.date

        # Actualiza estatus de facturacion del pedido de compra relacionado a una factura

            for line in self.invoice_line_ids:
                if line.product_id:
                    if line.stock_production_lot_id:
                        if self.type == 'in_invoice':
                            line.stock_production_lot_id.purchase_date = mydate

                        if self.type == 'out_invoice':
                            line.stock_production_lot_id.date_sold = mydate
                            line.stock_production_lot_id.sold_id = line.invoice_id.user_id.id
        return res

    @api.multi
    def action_invoice_paid(self):
        res = super(AccountInvoice, self).action_invoice_paid()
        mydate = date.today()

        for line in self.invoice_line_ids:
            if line.product_id:
                if line.stock_production_lot_id:
                    if self.type == 'out_invoice':
                        line.stock_production_lot_id.rcvd_pymnt = mydate
        return res


class AccountInvoiceLineSerial(models.Model):
    _inherit = 'account.invoice.line'

    stock_production_lot_id = fields.Many2one('stock.production.lot', copy=False)

    @api.onchange('stock_production_lot_id')
    def onchange_stock_production_lot_id(self):
        if self.stock_production_lot_id:
            self.name = self.product_id.display_name + " [" +  str(self.stock_production_lot_id.name) + "]"

