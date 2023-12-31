from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from werkzeug.urls import url_encode
		
class res_company(models.Model):
    _inherit = 'res.company'
    _name = 'res.company'
   
    #plafond_secu = fields.Float(string="Plafond de la Securite Sociale", required=True, default=6000)
    #nombre_employes = fields.Integer(string="Nombre d'employes")
    #cotisation_prevoyance = fields.Float(string="Cotisation Patronale Prevoyance")
    #org_ss = fields.Char(string="Organisme de sécurite sociale")
    #conv_coll = fields.Char(string="Convention collective")
    n_cnps = fields.Char(string="N° CNPS")
    cnps_ret_sal = fields.Float(string="Régime retraite %", default=6.3)
    cnps_ret_pat = fields.Float(string="Régime retraite %", default=7.7)
    cnps_at = fields.Float(string="Accident de Travail %", default=3)
    cnps_pf = fields.Float(string="Prestation Familliale %", default=5)

    salary_grid_ids = fields.One2many('salary.grid', 'company_id', string='Grille de Salaire', copy=False)

class salary_grid(models.Model):
    _name = 'salary.grid'

    name = fields.Char(string="Nom de catégorie")
    salary = fields.Float(string="Montant")
    company_id = fields.Many2one('res.company', string='Company',
        index=True, required=True, auto_join=True, ondelete="cascade",
        help="The salary_grid of this entry line.")


class HrEmployeePrivate(models.Model):
    _inherit = 'hr.employee'


    # code = fields.Char(string='Matricule', required=True, readonly=True, copy=False, default="/")
    n_cnps = fields.Char(string="N° CNPS", required=False)
    
   
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['registration_number'] = self.env['ir.sequence'].next_by_code('hr.employee') or _("/")

        # return super().create(vals_list)
            
            if vals.get('user_id'):
                user = self.env['res.users'].browse(vals['user_id'])
                vals.update(self._sync_user(user, bool(vals.get('image_1920'))))
                vals['name'] = vals.get('name', user.name)
        employees = super().create(vals_list)
        if self.env.context.get('salary_simulation'):
            return employees
        employee_departments = employees.department_id
        if employee_departments:
            self.env['mail.channel'].sudo().search([
                ('subscription_department_ids', 'in', employee_departments.ids)
            ])._subscribe_users_automatically()
        onboarding_notes_bodies = {}
        hr_root_menu = self.env.ref('hr.menu_hr_root')
        for employee in employees:
            employee._message_subscribe(employee.address_home_id.ids)
            # Launch onboarding plans
            url = '/web#%s' % url_encode({
                'action': 'hr.plan_wizard_action',
                'active_id': employee.id,
                'active_model': 'hr.employee',
                'menu_id': hr_root_menu.id,
            })
            onboarding_notes_bodies[employee.id] = _(
                '<b>Congratulations!</b> May I recommend you to setup an <a href="%s">onboarding plan?</a>',
                url,
            )
        employees._message_log_batch(onboarding_notes_bodies)
        return employees

    def write(self, vals):
        if self.registration_number == '/':
            vals['registration_number'] = self.env['ir.sequence'].next_by_code('hr.employee')
        if 'address_home_id' in vals:
            account_id = vals.get('bank_account_id') or self.bank_account_id.id
            if account_id:
                self.env['res.partner.bank'].browse(account_id).partner_id = vals['address_home_id']
            self.message_unsubscribe(self.address_home_id.ids)
            if vals['address_home_id']:
                self._message_subscribe([vals['address_home_id']])
        if 'user_id' in vals:
            # Update the profile pictures with user, except if provided 
            vals.update(self._sync_user(self.env['res.users'].browse(vals['user_id']),
                                        (bool(self.image_1920))))
        if 'work_permit_expiration_date' in vals:
            vals['work_permit_scheduled_activity'] = False
        res = super(HrEmployeePrivate, self).write(vals)
        if vals.get('department_id') or vals.get('user_id'):
            department_id = vals['department_id'] if vals.get('department_id') else self[:1].department_id.id
            # When added to a department or changing user, subscribe to the channels auto-subscribed by department
            self.env['mail.channel'].sudo().search([
                ('subscription_department_ids', 'in', department_id)
            ])._subscribe_users_automatically()
        return res

    def _compute_employee_duration(self, day_to=date.today()):
        r = relativedelta((day_to+ relativedelta(months=+1, day=1, days=0)), self.first_contract_date)
        #raise UserError(_(' %s \n (%s).') % (r.years, r.months))
        return r
    

class Contract(models.Model):
    """
    Employee contract based on the visa, work permits
    allows to configure different Salary structure
    """
    _inherit = 'hr.contract'
    _description = 'Employee Contract'


    wage_cat = fields.Many2one('salary.grid', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string='Wage category')
    up_wage = fields.Float(string='Sursalaire', default=0)
    wage = fields.Monetary('Wage', required=True, tracking=True, store="true", compute="_onchange_wage_cat", help="Employee's monthly gross wage.")
    
    
    @api.depends('wage_cat')
    def _onchange_wage_cat(self):
        for contract in self:
            if contract.wage_cat:
                contract.wage = contract.wage_cat.salary
            
            

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    def calculate_seniority(self):
        # Convertir la date de string à un objet datetime
        first_contract_date = self.employee_id.first_contract_date
        # Obtenir la date actuelle
        current_date = self.date_from
        # Calculer la différence entre les deux dates en années et mois
        years = current_date.year - first_contract_date.year
        months = current_date.month - first_contract_date.month

        # Si le mois actuel est antérieur au mois de début de contrat, réduire d'une année
        if current_date.month < first_contract_date.month:
            years -= 1
            months += 12
        if years == 0:
            return f"{months} mois"
        elif years == 1:
            return f"{years} an, {months} mois"
        else :
            return f"{years} ans, {months} mois"