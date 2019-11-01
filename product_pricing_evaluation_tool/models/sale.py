from odoo import api, fields, models
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        for record in self:
            for line in record.order_line:
                if line.product_id.calculation:
                    line.product_id.date_sold = datetime.now().date()
                    line.product_id.sold_id = self.env.user.id
        return super().action_confirm()
