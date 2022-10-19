"""
This Module is for API consumer-side reporting on QBv3 queries transactions.
It has "Profit & Loss" data retrieve function
"""

import calendar
from dateutil.rrule import *
from dateutil.parser import *
from datetime import *

try:
    from rauth import OAuth1Session, OAuth1Service
except:
    print("Please import Rauth:\n\n")
    print("http://rauth.readthedocs.org/en/latest/\n")


class QuickBooks():
    """A wrapper class around Python's Rauth module for Quickbooks the API"""

    access_token = ''
    access_token_secret = ''
    consumer_key = ''
    consumer_secret = ''
    company_id = 0
    callback_url = ''
    session = None

    base_url_v3 = "https://quickbooks.api.intuit.com/v3"
    base_url_v2 = "https://qbo.intuit.com/qbo1"

    request_token_url = "https://oauth.intuit.com/oauth/v1/get_request_token"
    access_token_url = "https://oauth.intuit.com/oauth/v1/get_access_token"

    authorize_url = "https://appcenter.intuit.com/Connect/Begin"

    # Things needed for authentication
    qbService = None

    request_token = ''
    request_token_secret = ''

    def __init__(self, **args):

        if 'cred_path' in args:
            self.read_creds_from_file(args['cred_path'])

        if 'consumer_key' in args:
            self.consumer_key = args['consumer_key']

        if 'consumer_secret' in args:
            self.consumer_secret = args['consumer_secret']

        if 'access_token' in args:
            self.access_token = args['access_token']

        if 'access_token_secret' in args:
            self.access_token_secret = args['access_token_secret']

        if 'company_id' in args:
            self.company_id = args['company_id']

        if 'callback_url' in args:
            self.callback_url = args['callback_url']

        if 'verbose' in args:
            self.verbose = True
        else:
            self.verbose = False

        self._BUSINESS_OBJECTS = [

            "Account", "Attachable", "Bill", "BillPayment",
            "Class", "CompanyInfo", "CreditMemo", "Customer",
            "Department", "Employee", "Estimate", "Invoice",
            "Item", "JournalEntry", "Payment", "PaymentMethod",
            "Preferences", "Purchase", "PurchaseOrder",
            "SalesReceipt", "TaxCode", "TaxRate", "Term",
            "TimeActivity", "Vendor", "VendorCredit"

        ]

    def set_up_service(self):
        self.qbService = OAuth1Service(
            name=None,
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            request_token_url=self.request_token_url,
            access_token_url=self.access_token_url,
            authorize_url=self.authorize_url,
            base_url=None
        )

    def get_authorize_url(self):
        """Returns the Authorize URL as returned by QB,
        and specified by OAuth 1.0a.
        :return URI:
        """
        if self.qbService is None:
            self.set_up_service()

        self.request_token, self.request_token_secret = self.qbService \
            .get_request_token(
            params={'oauth_callback': self.callback_url}
        )

        print
        self.request_token, self.request_token_secret

        return self.qbService.get_authorize_url(self.request_token)

    def get_access_tokens(self, oauth_verifier):
        """Wrapper around get_auth_session, returns session, and sets
        access_token and access_token_secret on the QB Object.
        :param oauth_verifier: the oauth_verifier as specified by OAuth 1.0a
        """
        session = self.qbService.get_auth_session(
            self.request_token,
            self.request_token_secret,
            data={'oauth_verifier': oauth_verifier})

        self.access_token = session.access_token
        self.access_token_secret = session.access_token_secret

        return session

    def create_session(self):
        if (self.consumer_secret and
                self.consumer_key and
                self.access_token_secret and
                self.access_token):
            session = OAuth1Session(self.consumer_key,
                                    self.consumer_secret,
                                    self.access_token,
                                    self.access_token_secret,
                                    )
            self.session = session
        else:
            raise Exception("Need four creds for Quickbooks.create_session.")
        return self.session

    def pnl(qbo_session, period="MONTHLY", start_date="first", end_date="last",
            **kwargs):
        """
        start_date and end_dates should be datetime objects if they're to be used
        kwargs are for filtering the QUERY, not the report here (and other
        functionality too...see below)
        """

        pnl_account_types = [

            "Income", "Other Income",
            "Expense", "Other Expense", "Cost of Goods Sold"

        ]

        # go through the accounts, collecting a list of those that are
        # pnl accounts

        relevant_accounts = []

        coa = qbo_session.chart_of_accounts()

        AccountType_i = coa[0].index("AccountType")
        fqa_i = coa[0].index("FullyQualifiedName")

        for a in coa:

            AccountType = a[AccountType_i]

            if AccountType in pnl_account_types:
                relevant_accounts.append(a[fqa_i])

        # now collect the ledger_lines that are even relevant to the time
        # period and pnl accounts (and we'll handle presentation last)

        relevant_activity = {}  # {account:[relevant lines]}

        all_ledger_lines = qbo_session.ledger_lines(None, None, None, True,
                                                    **kwargs)

        headers = all_ledger_lines[0]

        account_i = headers.index("account")
        amount_i = headers.index("amount")
        date_i = headers.index("TxnDate")

        earliest_date = datetime(2100, 1, 1)
        latest_date = datetime(1900, 1, 1)

        for line in all_ledger_lines[1:]:

            account = line[account_i]
            line_date = line[date_i]

            # first apply the date filter!
            if not start_date == "first" and line_date < start_date:
                continue

            if not end_date == "last" and line_date > end_date:
                continue

            # if it's made the cut, we can update the report date bounds
            earliest_date = min(line_date, earliest_date)
            latest_date = max(line_date, latest_date)

            # then apply the account filter!

            if not account in relevant_activity:
                # then let's confirm that its account type is a pnl one

                if not account in relevant_accounts:

                    continue

                else:
                    relevant_activity[account] = []

            relevant_activity[account].append(line)

        # now let's do presentation
        # TODO -- incorporate pandas tables...do only minimal work on it until then

        pnl_lines = []

        if period == "YEARLY":

            report_start_date = datetime(earliest_date.year, 1, 1)
            report_end_date = datetime(latest_date.year, 12, 31)

            period_start_dates = list(rrule(YEARLY, bymonth=1, bymonthday=1,
                                            dtstart=report_start_date,
                                            until=report_end_date))

            period_end_dates = list(rrule(YEARLY, bymonth=12, bymonthday=-1,
                                          dtstart=report_start_date,
                                          until=report_end_date))

        elif period == "MONTHLY":

            report_start_date = datetime(earliest_date.year,
                                         earliest_date.month,
                                         1)
            report_end_date = datetime(latest_date.year,
                                       latest_date.month,
                                       calendar.monthrange(latest_date.year,
                                                           latest_date.month)[1])

            period_start_dates = list(rrule(MONTHLY, bymonthday=1,
                                            dtstart=report_start_date,
                                            until=report_end_date))

            period_end_dates = list(rrule(YEARLY, bymonthday=-1,
                                          dtstart=report_start_date,
                                          until=report_end_date))

        header_1 = ["", "Period Start -->"] + period_start_dates
        header_2 = ["Account", "Period End -->"] + period_end_dates

        pnl_lines.append(header_1)
        pnl_lines.append(header_2)

        """Clearly, there's a way to do this with only one pass of the data...
        let's get that right in the first re-write...probably with pandas"""

        # now let's fill up the pnl_lines with what we know to be the relevant data
        # for now, we'll rely on the knowledge that the data is coming to us in
        # date order, but that should be fixed too...

        for account in relevant_activity:

            account_row = [account, ""]  # one value per period

            current_period_index = 0  # primitive counter, yes!
            this_period_total = 0  # this will be this period's total

            for line in relevant_activity[account]:

                line_amount = line[amount_i]
                line_date = line[date_i]

                if line_date > period_end_dates[current_period_index]:

                    account_row.append(this_period_total)
                    this_period_total = line_amount
                    current_period_index += 1

                else:

                    this_period_total = round(this_period_total +
                                              line_amount, 2)

            """super sloppy..."""
            account_row.append(this_period_total)  # for the last period
            current_period_index += 1

            while current_period_index < len(period_end_dates):
                account_row.append(0)
                current_period_index += 1

            pnl_lines.append(account_row)

        return pnl_lines
