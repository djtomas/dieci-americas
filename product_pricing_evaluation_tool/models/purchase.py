from odoo import api, fields, models
from datetime import datetime, timedelta


class SaleOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def button_confirm(self):
        for record in self:
            for line in record.order_line:
                if line.product_id.calculation:
                    line.product_id.purchase_date = datetime.now().date()
        return super().button_confirm()