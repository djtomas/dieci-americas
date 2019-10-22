# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    es_vendedor_avanzado = fields.Boolean('Vendedor Avansado', compute="_calcular_avanzado")

    user_id = fields.Many2one('res.users', string='Responsable', track_visibility='onchange',
                              default=lambda self: self.env.user)

    @api.one
    @api.depends('user_id')
    def _calcular_avanzado(self):
        self.es_vendedor_avanzado = self.env.user.has_group('sale_advanced_seller.advanced_seller_group')