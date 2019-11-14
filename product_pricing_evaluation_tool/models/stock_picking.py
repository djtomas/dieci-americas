from odoo import api, fields, models
from datetime import datetime, timedelta


class StockPickingEvaluation(models.Model):
    _inherit = 'stock.picking'

    """
    @api.multi
    def button_confirm(self):
        for record in self:
            for line in record.order_line:
                if line.product_id.calculation:
                    line.product_id.purchase_date = datetime.now().date()
        return super().button_confirm()
        """

    @api.multi
    def do_transfer(self):
        res = super(StockPickingEvaluation, self).do_transfer()
        print("1")
        for move in self.move_ids_without_packege:
            print("2")
            print(move.product_id.name)
        return res