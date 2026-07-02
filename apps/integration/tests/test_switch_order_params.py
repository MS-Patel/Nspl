import pytest

from apps.integration.utils import get_bse_switch_order_params
from apps.investments.factories import FolioFactory, OrderFactory
from apps.investments.models import Order
from apps.products.factories import AMCFactory, SchemeFactory
from apps.users.factories import DistributorProfileFactory, InvestorProfileFactory


@pytest.mark.django_db
def test_switch_order_params_match_wsdl_for_amount_switch():
    amc = AMCFactory()
    distributor = DistributorProfileFactory(broker_code="SUB001", euin="E123456")
    investor = InvestorProfileFactory(
        distributor=distributor,
        ucc_code="TEST001",
        pan="ABCDE1234F",
    )
    source_scheme = SchemeFactory(scheme_code="SRC001", amc=amc)
    target_scheme = SchemeFactory(scheme_code="TGT001", amc=amc)
    folio = FolioFactory(investor=investor, amc=amc, folio_number="12345/67")
    order = OrderFactory(
        investor=investor,
        distributor=distributor,
        scheme=source_scheme,
        target_scheme=target_scheme,
        folio=folio,
        transaction_type=Order.SWITCH,
        amount=5000,
        units=0,
        all_redeem=False,
        unique_ref_no="123456",
        is_new_folio=False,
        euin="",
    )

    params = get_bse_switch_order_params(
        order,
        member_id="MEMBER1",
        user_id="USER1",
        password="enc_password",
        pass_key="pass_key",
    )

    assert params == {
        "TransCode": "NEW",
        "TransNo": "123456",
        "OrderId": "",
        "UserId": "USER1",
        "MemberId": "MEMBER1",
        "ClientCode": "TEST001",
        "FromSchemeCd": "SRC001",
        "ToSchemeCd": "TGT001",
        "BuySell": Order.SWITCH,
        "BuySellType": "ADDITIONAL",
        "DPTxn": "P",
        "OrderVal": "5000.00",
        "SwitchUnits": "0",
        "AllUnitsFlag": "N",
        "FolioNo": "12345/67",
        "Remarks": "",
        "KYCStatus": "Y",
        "SubBrCode": "SUB001",
        "Euin": "E123456",
        "EuinVal": "Y",
        "MinRedeem": "N",
        "IPAdd": "",
        "Password": "enc_password",
        "PassKey": "pass_key",
        "Parma1": "",
        "Param2": "",
        "Param3": "",
        "Filler1": "",
        "Filler2": "",
        "Filler3": "",
        "Filler4": "",
        "Filler5": "",
        "Filler6": "",
    }


@pytest.mark.django_db
def test_switch_order_params_use_all_units_flag_for_full_switch():
    amc = AMCFactory()
    investor = InvestorProfileFactory(ucc_code="TEST002", pan="ABCDE1234G")
    source_scheme = SchemeFactory(scheme_code="SRC002", amc=amc)
    target_scheme = SchemeFactory(scheme_code="TGT002", amc=amc)
    order = OrderFactory(
        investor=investor,
        distributor=investor.distributor,
        scheme=source_scheme,
        target_scheme=target_scheme,
        transaction_type=Order.SWITCH,
        amount=0,
        units=0,
        all_redeem=True,
        unique_ref_no="654321",
    )

    params = get_bse_switch_order_params(
        order,
        member_id="MEMBER1",
        user_id="USER1",
        password="enc_password",
        pass_key="pass_key",
    )

    assert params["AllUnitsFlag"] == "Y"
    assert params["OrderVal"] == "0"
    assert params["SwitchUnits"] == "0"
