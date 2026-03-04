-- =============================================================================
-- SkillMeat Backstage Integration Demo -- Financial Services Sample Data
-- =============================================================================
-- This script seeds the demo_finserv database with realistic (but fictional)
-- fin-serv tables used in the IDP scaffold demo templates.
--
-- Tables:
--   accounts          -- Customer / institutional accounts
--   transactions      -- Account transaction ledger
--   compliance_checks -- Compliance review records tied to transactions
--   audit_log         -- Immutable audit trail for regulated operations
-- =============================================================================

-- ---------------------------------------------------------------------------
-- ACCOUNTS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
    id              SERIAL PRIMARY KEY,
    account_number  VARCHAR(20)  NOT NULL UNIQUE,
    holder_name     VARCHAR(120) NOT NULL,
    account_type    VARCHAR(30)  NOT NULL CHECK (account_type IN (
                        'checking', 'savings', 'investment', 'custody', 'trust'
                    )),
    currency        CHAR(3)      NOT NULL DEFAULT 'USD',
    balance         NUMERIC(18, 2) NOT NULL DEFAULT 0.00,
    status          VARCHAR(20)  NOT NULL DEFAULT 'active' CHECK (status IN (
                        'active', 'suspended', 'closed', 'under_review'
                    )),
    risk_tier       VARCHAR(10)  NOT NULL DEFAULT 'standard' CHECK (risk_tier IN (
                        'low', 'standard', 'elevated', 'high'
                    )),
    opened_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

INSERT INTO accounts (account_number, holder_name, account_type, currency, balance, status, risk_tier) VALUES
    ('ACC-0001-US', 'Apex Capital Partners',    'investment', 'USD', 42500000.00, 'active',       'elevated'),
    ('ACC-0002-US', 'Meridian Trust Co.',        'trust',      'USD',  8750000.00, 'active',       'standard'),
    ('ACC-0003-US', 'Northbrook Savings LLC',    'savings',    'USD',   125000.00, 'active',       'low'),
    ('ACC-0004-US', 'Quantum Asset Management',  'custody',    'USD', 97300000.00, 'active',       'high'),
    ('ACC-0005-US', 'Helena Strauss',            'checking',   'USD',    18450.75, 'active',       'low'),
    ('ACC-0006-US', 'Orion Hedge Fund Ltd.',     'investment', 'USD', 15600000.00, 'under_review', 'elevated'),
    ('ACC-0007-US', 'Clearwater Municipal Fund', 'investment', 'USD',  3200000.00, 'active',       'standard'),
    ('ACC-0008-US', 'James R. Whitfield III',    'savings',    'USD',    54200.00, 'suspended',    'standard')
ON CONFLICT (account_number) DO NOTHING;

-- ---------------------------------------------------------------------------
-- TRANSACTIONS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    txn_reference   VARCHAR(40)   NOT NULL UNIQUE,
    account_id      INT           NOT NULL REFERENCES accounts(id),
    direction       CHAR(6)       NOT NULL CHECK (direction IN ('credit', 'debit')),
    amount          NUMERIC(18, 2) NOT NULL CHECK (amount > 0),
    currency        CHAR(3)       NOT NULL DEFAULT 'USD',
    description     VARCHAR(255),
    counterparty    VARCHAR(120),
    channel         VARCHAR(30)   NOT NULL DEFAULT 'api' CHECK (channel IN (
                        'api', 'wire', 'ach', 'internal', 'swift', 'fx'
                    )),
    status          VARCHAR(20)   NOT NULL DEFAULT 'settled' CHECK (status IN (
                        'pending', 'settled', 'reversed', 'flagged', 'rejected'
                    )),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

INSERT INTO transactions (txn_reference, account_id, direction, amount, description, counterparty, channel, status) VALUES
    ('TXN-2025-000001', 1, 'credit', 5000000.00,  'Q4 Capital Injection',       'Apex GP Entity',           'wire',     'settled'),
    ('TXN-2025-000002', 1, 'debit',   750000.00,  'Management Fee Q4',          'Apex Capital Partners GP', 'internal', 'settled'),
    ('TXN-2025-000003', 2, 'credit',  125000.00,  'Trust Distribution Dec-24',  'Meridian Beneficiary A',   'ach',      'settled'),
    ('TXN-2025-000004', 4, 'credit', 10000000.00, 'Custody Transfer In',        'Deutsche Bank NY',         'swift',    'settled'),
    ('TXN-2025-000005', 5, 'debit',    1200.50,   'Mortgage Payment Jan-25',    'First National Bank',      'ach',      'settled'),
    ('TXN-2025-000006', 6, 'credit',  3500000.00, 'Investor Subscription',      'Cayman Feeder Fund I',     'swift',    'flagged'),
    ('TXN-2025-000007', 6, 'debit',   250000.00,  'Performance Fee Withdrawal', 'Orion Management Ltd.',    'wire',     'flagged'),
    ('TXN-2025-000008', 7, 'credit',   200000.00, 'Municipal Bond Coupon',      'US Treasury / Clearing',   'internal', 'settled'),
    ('TXN-2025-000009', 3, 'debit',    40000.00,  'Operational Expense',        'Various Vendors',          'ach',      'pending'),
    ('TXN-2025-000010', 1, 'credit', 1000000.00,  'FX Conversion EUR->USD',     'Barclays FX Desk',         'fx',       'settled')
ON CONFLICT (txn_reference) DO NOTHING;

-- ---------------------------------------------------------------------------
-- COMPLIANCE_CHECKS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compliance_checks (
    id              SERIAL PRIMARY KEY,
    txn_id          INT           NOT NULL REFERENCES transactions(id),
    check_type      VARCHAR(40)   NOT NULL CHECK (check_type IN (
                        'aml_screening', 'kyc_verification', 'sanctions_check',
                        'large_cash_report', 'suspicious_activity', 'pep_screening'
                    )),
    result          VARCHAR(20)   NOT NULL CHECK (result IN (
                        'pass', 'fail', 'review_required', 'escalated'
                    )),
    risk_score      NUMERIC(5, 2) CHECK (risk_score BETWEEN 0 AND 100),
    notes           TEXT,
    reviewed_by     VARCHAR(80),
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

INSERT INTO compliance_checks (txn_id, check_type, result, risk_score, notes, reviewed_by, reviewed_at) VALUES
    (1,  'aml_screening',     'pass',            4.2,  'Standard wire transfer within known pattern', 'system',          NOW() - INTERVAL '5 days'),
    (1,  'sanctions_check',   'pass',            1.0,  'Counterparty cleared against OFAC/EU lists',  'system',          NOW() - INTERVAL '5 days'),
    (4,  'aml_screening',     'pass',            8.5,  'Large custody transfer -- auto-approved',      'system',          NOW() - INTERVAL '3 days'),
    (4,  'large_cash_report', 'pass',           NULL,  'CTR filed with FinCEN ref CTR-2025-00441',     'compliance_team', NOW() - INTERVAL '3 days'),
    (6,  'aml_screening',     'review_required', 68.0, 'Subscription from high-risk jurisdiction',    'aml_officer',     NOW() - INTERVAL '1 day'),
    (6,  'sanctions_check',   'escalated',       82.5, 'Partial name match on OFAC SDN list',         'compliance_lead', NOW() - INTERVAL '1 day'),
    (6,  'pep_screening',     'review_required', 55.0, 'Beneficial owner is a PEP (Level 2)',         'aml_officer',     NOW() - INTERVAL '1 day'),
    (7,  'suspicious_activity','escalated',      90.0, 'SAR filed -- case ID SAR-2025-00812',          'compliance_lead', NOW()),
    (3,  'kyc_verification',  'pass',            10.0, 'Beneficiary KYC on file and current',         'system',          NOW() - INTERVAL '10 days'),
    (10, 'aml_screening',     'pass',             5.5, 'FX conversion within approved limits',         'system',          NOW() - INTERVAL '2 days')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- AUDIT_LOG
-- Append-only table -- no updates or deletes allowed in production.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    event_type      VARCHAR(60)  NOT NULL,
    actor           VARCHAR(120) NOT NULL,
    actor_system    VARCHAR(60),
    target_entity   VARCHAR(60),
    target_id       VARCHAR(40),
    payload         JSONB,
    ip_address      INET,
    logged_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

INSERT INTO audit_log (event_type, actor, actor_system, target_entity, target_id, payload) VALUES
    ('account.status_change',     'compliance_lead', 'backstage-idp',  'accounts',     '6',   '{"old_status":"active","new_status":"under_review","reason":"AML investigation"}'),
    ('account.status_change',     'risk_officer',    'backstage-idp',  'accounts',     '8',   '{"old_status":"active","new_status":"suspended","reason":"KYC refresh overdue"}'),
    ('transaction.flagged',       'aml_system',      'rule-engine-v3', 'transactions', '6',   '{"rule":"HIGH_RISK_JURISDICTION","score":68.0}'),
    ('transaction.flagged',       'aml_system',      'rule-engine-v3', 'transactions', '7',   '{"rule":"SUSPICIOUS_WITHDRAWAL_PATTERN","score":90.0}'),
    ('compliance.sar_filed',      'compliance_lead', 'backstage-idp',  'compliance',   'SAR-2025-00812', '{"txn_ids":[6,7],"filed_with":"FinCEN"}'),
    ('compliance.ctr_filed',      'compliance_team', 'backstage-idp',  'compliance',   'CTR-2025-00441', '{"txn_id":4,"amount":10000000.00}'),
    ('scaffold.service_created',  'platform_team',   'backstage-idp',  'service',      'payment-processor-v2', '{"template":"skillmeat:finserv-microservice","owner":"payments-squad"}'),
    ('scaffold.secret_injected',  'platform_team',   'backstage-idp',  'service',      'payment-processor-v2', '{"secret":"db-credentials","vault_path":"secret/finserv/payment-processor-v2"}')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- INDEXES (query performance for demo API calls)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_transactions_account_id  ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status       ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at   ON transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_compliance_txn_id         ON compliance_checks(txn_id);
CREATE INDEX IF NOT EXISTS idx_compliance_result         ON compliance_checks(result);
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type      ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_logged_at       ON audit_log(logged_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_target          ON audit_log(target_entity, target_id);
