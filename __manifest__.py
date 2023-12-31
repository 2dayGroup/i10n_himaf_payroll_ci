# Copyright 2010-2014 Savoir-faire Linux (<http://www.savoirfairelinux.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "COTE D'IVOIRE - PAIE",
    "version": "16.0.1.0.1",
    "author": "2DAY GROUP",
    "maintainer": "2DAY GROUP",
    "website": "2daygroup.net",
    "license": "AGPL-3",
    "category": "Human Resources",
    "summary": "Paie pour la Cote d'Ivoire",
    "depends": ["hr", "hr_payroll"],
    "data": [
        "data/ir_sequence_data.xml",
        "data/i10n_himaf_payroll_ci_data.xml",
        'data/paper_format.xml',
        'views/report_payslip_templates.xml',
        'views/report_layout.xml',
        'views/hr_salary_rule_view.xml',
        "views/hr_view.xml", "views/base_config_view.xml", "views/i10n_himaf_payroll_view.xml",
        'security/ir.model.access.csv',
        ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    'css': [
        'static/src/css/report.css'
    ],
    "images":['static/description/Banner.png'],
}
