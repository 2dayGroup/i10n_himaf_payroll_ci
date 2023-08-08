# -*- coding: utf-8 -*-
from datetime import date, datetime, time
import logging
from dateutil.relativedelta import relativedelta
from odoo import _, api, models, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

UPDATE_PARTNER_FIELDS = ["firstname", "lastname", "user_id", "address_home_id"]


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    
    n_cnps = fields.Char(string="N° CNPS", required=False)
    n_part = fields.Float(string="Part IGR", required=True, default=1, compute='_compute_employee_igr_part', store=True)
    # duration = fields.Char(string="Duration", required=False)

    @api.model
    def _names_order_default(self):
        return "last_first"

    @api.model
    def _get_names_order(self):
        """Get names order configuration from system parameters.
        You can override this method to read configuration from language,
        country, company or other"""
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("employee_names_order", self._names_order_default())
        )

    @api.model
    def _get_name(self, lastname, firstname):
        order = self._get_names_order()
        if order == "last_first_comma":
            return ", ".join(p for p in (lastname, firstname) if p)
        elif order == "first_last":
            return " ".join(p for p in (firstname, lastname) if p)
        else:
            return " ".join(p for p in (lastname, firstname) if p)

    @api.onchange("firstname", "lastname")
    def _onchange_firstname_lastname(self):
        if self.firstname or self.lastname:
            self.name = self._get_name(self.lastname, self.firstname)

    @api.model
    def _is_partner_firstname_installed(self):
        return bool(
            self.env["ir.module.module"]
            .sudo()
            .search([("name", "=", "partner_firstname"), ("state", "=", "installed")])
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._prepare_vals_on_create_firstname_lastname(vals)
        res = super().create(vals_list)
        if self._is_partner_firstname_installed():
            for employee in res:
                employee._update_partner_firstname()
        return res

    def write(self, vals):
        self._prepare_vals_on_write_firstname_lastname(vals)
        res = super().write(vals)
        if self._is_partner_firstname_installed() and set(vals).intersection(
            UPDATE_PARTNER_FIELDS
        ):
            self._update_partner_firstname()
        return res

    def _prepare_vals_on_create_firstname_lastname(self, vals):
        if vals.get("firstname") or vals.get("lastname"):
            vals["name"] = self._get_name(vals.get("lastname"), vals.get("firstname"))
        elif vals.get("name"):
            vals["lastname"] = self.split_name(vals["name"])["lastname"]
            vals["firstname"] = self.split_name(vals["name"])["firstname"]
        else:
            raise ValidationError(_("No name set."))

    def _prepare_vals_on_write_firstname_lastname(self, vals):
        if "firstname" in vals or "lastname" in vals:
            if "lastname" in vals:
                lastname = vals.get("lastname")
            else:
                lastname = self.lastname
            if "firstname" in vals:
                firstname = vals.get("firstname")
            else:
                firstname = self.firstname
            vals["name"] = self._get_name(lastname, firstname)
        elif vals.get("name"):
            vals["lastname"] = self.split_name(vals["name"])["lastname"]
            vals["firstname"] = self.split_name(vals["name"])["firstname"]

    @api.model
    def _get_whitespace_cleaned_name(self, name, comma=False):
        """Remove redundant whitespace from :param:`name`.

        Removes leading, trailing and duplicated whitespace.
        """
        try:
            name = " ".join(name.split()) if name else name
        except UnicodeDecodeError:
            name = " ".join(name.decode("utf-8").split()) if name else name

        if comma:
            name = name.replace(" ,", ",").replace(", ", ",")
        return name

    @api.model
    def _get_inverse_name(self, name):
        """Compute the inverted name.

        This method can be easily overriden by other submodules.
        You can also override this method to change the order of name's
        attributes

        When this method is called, :attr:`~.name` already has unified and
        trimmed whitespace.
        """
        order = self._get_names_order()
        # Remove redundant spaces
        name = self._get_whitespace_cleaned_name(
            name, comma=(order == "last_first_comma")
        )
        parts = name.split("," if order == "last_first_comma" else " ", 1)
        if len(parts) > 1:
            if order == "first_last":
                parts = [" ".join(parts[1:]), parts[0]]
            else:
                parts = [parts[0], " ".join(parts[1:])]
        else:
            while len(parts) < 2:
                parts.append(False)
        return {"lastname": parts[0], "firstname": parts[1]}

    @api.model
    def split_name(self, name):
        clean_name = " ".join(name.split(None)) if name else name
        return self._get_inverse_name(clean_name)

    def _inverse_name(self):
        """Try to revert the effect of :meth:`._compute_name`."""
        for record in self:
            parts = self._get_inverse_name(record.name)
            record.lastname = parts["lastname"]
            record.firstname = parts["firstname"]

    @api.model
    def _install_employee_firstname(self):
        """Save names correctly in the database.

        Before installing the module, field ``name`` contains all full names.
        When installing it, this method parses those names and saves them
        correctly into the database. This can be called later too if needed.
        """
        # Find records with empty firstname and lastname
        records = self.search([("firstname", "=", False), ("lastname", "=", False)])

        # Force calculations there
        records._inverse_name()
        _logger.info("%d employees updated installing module.", len(records))

    def _update_partner_firstname(self):
        for employee in self:
            partners = employee.mapped("user_id.partner_id")
            partners |= employee.mapped("address_home_id")
            partners.write(
                {"firstname": employee.firstname, "lastname": employee.lastname}
            )

    @api.constrains("firstname", "lastname")
    def _check_name(self):
        """Ensure at least one name is set."""
        for record in self:
            if not (record.firstname or record.lastname):
                raise ValidationError(_("No name set."))

    
    def _compute_employee_duration(self, day_to=date.today()):
        r = relativedelta((day_to+ relativedelta(months=+1, day=1, days=0)), self.first_contract_date)
        #raise UserError(_(' %s \n (%s).') % (r.years, r.months))
        return r
    
    
    @api.depends('marital', 'children')
    def _compute_employee_igr_part(self):
        for employee in self:
            
            N = 1
            #if self.marital == 'single' or self.marital == 'widower' or self.marital == 'divorced' and self.senior_children:
            #    N = 1.5

            if (employee.marital == 'single' or employee.marital == 'divorced' ) and employee.children > 0:
                N = 2

            if employee.marital == 'widower' and employee.children > 0:
                N = 2.5

            if employee.marital == 'married':
                N = 2
            if employee.children > 0:
                N = 2.5

            if employee.children > 1:
                N += (employee.children - 1) *0.5

            if N > 5:
                N = 5
                
            employee.n_part = N