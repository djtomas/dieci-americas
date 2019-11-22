# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
        
    invoice_number_eva = fields.Char(
        string='Invoice Number', default='0',
        help="Invoice Number", copy=False)
    """
    @api.multi
    def action_invoice_open(self):
        ''' Herencia de metodo original de validacion de facturas.'''
        res = super(AccountInvoice, self).action_invoice_open()

        # Actualiza estatus de facturacion del pedido de compra relacionado a una factura
        if self.type == 'in_invoice':
            for line in self.invoice_line_ids:
                if line.product_id:
                    if line.product_id.
        return res
        """
