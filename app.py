from flask import Flask, redirect, url_for, render_template, request, session, flash
from firebird.connectfdb import con_to_firebird, con_to_firebird2 

from collections import defaultdict
import json
import datetime
import time
from datetime import timedelta, datetime
import hashlib
import logging


# Log configuration
logging.basicConfig(filename="logfilename.log", level=logging.INFO)


# ПОЛЗВА СЕ ЗА ПРОМЯНА НА ДАТТА ПО НАШИЯ СТАНДАРТ, МОЖЕ ДА СЕ ДОБАВЯТ И ДРУГИ ФОРМАТИ
context = {"now": int(time.time()), "strftime": time.strftime,
           "strptime": datetime.strptime}

app = Flask(__name__)

app.config["SECRET_KEY"] = "Bork@"

# Some staff used for card reservation


def generate_dates_range():
    """
        Generate list with dates for card
    """
    today = datetime.now().date()
    dates = []
    numdays = 40
    for x in range(0, numdays):
        new_date = today + timedelta(days=x)
        dates.append(new_date.strftime("%d.%m.%Y"))
    return dates


@app.route("/insertdata/<string:name>")
def insertdata(name):
    """
    МИНАВАМЕ ПРЕЗ ТОЗИ ТЕМПЛЕЙТ, ЗА ДА СЕ ПОПЪЛНИ ДАТАТА
    """
    return render_template("base.html", action=name)


@app.route("/", methods=["GET"])
def index():
    if not session.get("logged_in"):
        return render_template("login.html")
    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return redirect(url_for("info"))


@app.route("/login", methods=["POST"])
def login():
    user_credential = hashlib.sha256()
    password_credential = hashlib.sha256()
    user_credential.update(request.form["username"].encode('utf-8'))
    password_credential.update(request.form["password"].encode('utf-8'))
    if user_credential.hexdigest() == "694f9239193cd42447a703b48e6759b6c9917587064798bb14ad020a3b3b8539" and password_credential.hexdigest() == "694f9239193cd42447a703b48e6759b6c9917587064798bb14ad020a3b3b8539":
        session.permanent = False
        session["logged_in"] = True
        logging.info(f"[+] IP {request.remote_addr} connect Succsessfully at {datetime.now()}")
        return redirect(url_for("housekeeping"))
    else:
        logging.info(f"IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        flash("wrong autentication")
        return index()


@app.route("/logout")
def logout():
    session["logged_in"] = False
    return index()


@app.route("/info", methods=["GET", "POST"])
def info():
    """Списък с настанените гости в списъка гости"""
    if session.get("logged_in") is True:
        action = "/info"
        query = """
        WITH TMP_SMT AS (
        SELECT
        ACTIVE_NAST.NAST_ID,
        SUM(SMETKI_EL.KOL * ROUND(SMETKI_EL.SUMA,2)) AS SUMA
        FROM
        ACTIVE_NAST INNER JOIN SMETKI_EL ON ACTIVE_NAST.NAST_ID = SMETKI_EL.DEF_NAST_ID
        WHERE
        NOT EXISTS(SELECT SMT.ID FROM SMT_PAY_NODE SMT WHERE SMT.SMETKA_EL_ID = SMETKI_EL.ID)
        GROUP BY 1
        )

        SELECT
        COALESCE(BULGARIANS.NAME, 'НЕ ВЪВЕДЕНО'),
        NAST.CHECK_IN_DATE,
        DATEADD(NAST.DAYS DAY TO NAST.CHECK_IN_DATE),
        NAST.DAYS,
        ROOMS.NAME,
        DOGOVORI.NAME_CYR,
        DATEDIFF(DAY FROM NAST.CHECK_IN_DATE TO CURRENT_DATE),
        COALESCE(TMP_SMT.SUMA, 0.00),
        NAST.ID
        FROM
        ACTIVE_NAST INNER JOIN NAST ON NAST.ID = ACTIVE_NAST.NAST_ID
        INNER JOIN ROOMS ON ROOMS.ID = NAST.ROOM_ID
        INNER JOIN DOGOVORI ON DOGOVORI.ID = NAST.DOGOVOR_ID
        LEFT JOIN BULGARIANS ON NAST.BUL_ID = BULGARIANS.ID
        LEFT JOIN TMP_SMT ON TMP_SMT.NAST_ID = ACTIVE_NAST.NAST_ID
        ORDER BY 5
        """
        fdb_data = con_to_firebird(query)
        return render_template("index.html", action=action, fdb_data=fdb_data, title="гости", **context)
    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        flash("wrong autentication")
        return index()


@app.route("/info/<int:guest_id>")
def detail_info(guest_id):
    if session.get("logged_in"):
        """
        ДЕТЕЙЛИТЕ НА СМЕТАТА, ВИКАТ СЕ В МОДАЛНИЯТ ДИАЛОГ
        """
        query = """
        select
        coalesce(usl.name_cyr, 'Търговски обект'),
        sum((smetki_el.kol * ROUND(smetki_el.suma, 2)))
        from SMETKI_EL
        left join price on price.id = smetki_el.price_id
        left join usl on usl.id = price.usl_id
        inner join NAST on NAST.ID = SMETKI_EL.DEF_NAST_ID
        where smetki_el.def_nast_id = ?
        and not exists (select smt_pay_node.id from smt_pay_node where smt_pay_node.smetka_el_id = smetki_el.id)
        group by usl.name_cyr
        """
        fdb_data_smetka_el = con_to_firebird(query, (guest_id,))
        detail_data = {}
        for line in fdb_data_smetka_el:
            detail_data[line[0]] = line[1]
        return detail_data
    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        flash("wrong autentication")
        return index()


@app.route("/reservations", methods=["GET", "POST"])
def reservations():
    """
    СПИСЪК С РЕЗЕРАЦИИ
    """
    if session.get("logged_in"):
        # action = "/reservations"
        if request.method == "GET":
            return redirect(url_for("insertdata"))
        else:
            query = """
            select
            nast.reserve_id as res_id,
            nast.check_in_date as check_in,
            dateadd(nast.days day to nast.check_in_date) as check_out,
            nast.days as days,
            List(distinct(rooms.name)) as rooms,
            dogovori.name_cyr as dogovor,
            reserve.fromwho as fromwho,
            reserve.tel as telephone,
            coalesce(nast.vaucher, '') as vauc,
            coalesce(usl.name_cyr, '') as pans,
            sum(smetki_el.kol * smetki_el.suma) as smetkata,
            coalesce(reserve_type.name_cyr, 'Без статус')
            from nast
            inner join rooms on rooms.id = nast.room_id
            inner join dogovori on dogovori.id = nast.dogovor_id
            inner join reserve on reserve.id = nast.reserve_id
            left join pansion on pansion.id = nast.pansion_id
            left join usl on pansion.usl_id = usl.id
            inner join smetki_el on smetki_el.nast_id = nast.id
            left join reserve_type on reserve_type.id = reserve.reserve_type_id
            where nast.check_in_date between ? and ?
            and nast.last_opr_type not in (2, 4, 101)
            and nast.is_deleted = 0
            and NOT EXISTS(SELECT active_nast.nast_id from active_nast WHERE active_nast.nast_id = nast.id)
            group by 1,2,3,4,6,7,8,9,10,12
            """
            # Perspectivna zaetost
            q = """
            with table_one as
            (
            select
                room_tip.name_cyr as rn,
                count(distinct(nast.room_id)) as rc
                from nast
                inner join rooms on rooms.id = nast.room_id
                inner join room_tip on room_tip.id = rooms.room_tip_id
                inner join dogovori on dogovori.id = nast.dogovor_id
                where NAST.CHECK_IN_DATE <= ? AND DATEADD(NAST.DAYS-1 DAY TO NAST.CHECK_IN_DATE) >= ?
                and nast.is_deleted = 0
                and nast.last_opr_type not in (101, 4)
                group by 1
            )
            select
            table_one.rn,
            table_one.rc,
            (
                select count(room_tip.name_cyr) as total_br from room_tip
                inner join rooms on rooms.room_tip_id = room_tip.id
                where room_tip.name_cyr = table_one.rn
            ) as ttt
            from table_one

            """
            result = defaultdict(list)
            # End of perp zaetos
            f_data = request.form["fdata"] or str(datetime.today().date())
            l_data = request.form["ldata"] or str(datetime.today().date())

            dates = datetime.strptime(
                l_data, "%Y-%m-%d") - datetime.strptime(f_data, "%Y-%m-%d")
            for i in range(dates.days + 1):
                day = datetime.strptime(f_data, "%Y-%m-%d") + timedelta(days=i)
                for line in con_to_firebird(q, (str(day)[:-9], str(day)[:-9])):
                    result[str(day)[:-9]].append(line)
            Result = dict(result)

            fdb_reservations = con_to_firebird(
                query,
                (
                    f_data,
                    l_data,
                ),
            )
            return render_template(
                "reservations.html",
                f_data=f_data,
                l_data=l_data,
                fdb_reservations=fdb_reservations,
                title="резервации",
                Result=Result,
                **context
            )
    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()


@app.route("/usls", methods=["GET", "POST"])
def usls():
    """
    НАЧИСЛЕНИ И ПЛАТЕНО УСЛУГИ ЗА ПЕРИДО, ПОЛЗВАТ СЕ 2 КУЕРИТЕ, ЩОТО МИСЛЯ ДА СЕ ДОБАВЯ ОЩЕ!
    """
    if session.get("logged_in"):
        # action = "/usls"
        if request.method == "GET":
            return redirect(url_for("insertdata"))
        else:
            query_paid = """
            select
            case
            when SMETKI_EL.PRICE_ID is not null then case
            when USL.STATUS = '1' then USL_GRUPI.NAME_CYR
            when USL.STATUS = '2' then 'Нощувки'
            when USL.STATUS = '3' then 'Пансиони'
            end
            when SMETKI_EL.PRICE_ID is null then 'Търговски обект'
            end,
            sum(smt_pay_node.SUMA),
            sum(smt_pay_node.SUMA/(dds_stavka.dds/100+1))
            from PAYMENT_EL
            inner join SMETKA on SMETKA.ID = PAYMENT_EL.SMETKA_ID
            inner join OPR on OPR.ID = SMETKA.OPR_ID
            inner join SMT_PAY_NODE on SMT_PAY_NODE.PAYMENT_EL_ID = PAYMENT_EL.ID
            inner join SMETKI_EL on SMETKI_EL.ID = SMT_PAY_NODE.SMETKA_EL_ID
            left join PRICE on PRICE.ID = SMETKI_EL.PRICE_ID
            left join USL on USL.ID = PRICE.USL_ID
            left join NAST on NAST.ID = SMETKI_EL.NAST_ID
            left join ROOMS on ROOMS.ID = NAST.ROOM_ID
            inner join PAY_TIP on PAY_TIP.ID = PAYMENT_EL.PAY_TIP_ID
            left join USL_GRUPI on USL_GRUPI.ID = USL.GRUPA_ID
            inner join dds_stavka on dds_stavka.id = smetki_el.dds_id
            where (OPR.OPR_TIP_ID = '9' or OPR.OPR_TIP_ID = '6') and
            cast(OPR.DATE_TIME as date) between ? and ? and
            PAYMENT_EL.ID = SMT_PAY_NODE.PAYMENT_EL_ID
            group by 1
            order by 1
            """
            query_accrued = """
            select
            case
            when SMETKI_EL.PRICE_ID is not null then case
            when USL.STATUS = '1' then USL_GRUPI.NAME_CYR
            when USL.STATUS = '2' then 'Нощувки'
            when USL.STATUS = '3' then 'Пансиони'
            end
            when SMETKI_EL.PRICE_ID is null then 'Ресторант'
            end,
            sum(smetki_el.suma),
            sum(smetki_el.SUMA/(dds_stavka.dds/100+1))
            from smetki_el
            left join rooms on rooms.id = smetki_el.room_id
            inner join opr on opr.id = smetki_el.opr_id
            left join PRICE on PRICE.ID = SMETKI_EL.PRICE_ID
            left join USL on USL.ID = PRICE.USL_ID
            left join USL_GRUPI on USL_GRUPI.ID = USL.GRUPA_ID
            inner join dds_stavka on dds_stavka.id = smetki_el.dds_id
            where
            smetki_el.for_date between ? and ?
            and
            opr.id != '0'
            group by 1
                """
            f_data = request.form["fdata"] or str(datetime.today().date())
            l_data = request.form["ldata"] or str(datetime.today().date())
            fdb_reservations_paid = con_to_firebird(
                query_paid,
                (
                    f_data,
                    l_data,
                ),
            )
            fdb_reservations_accured = con_to_firebird(
                query_accrued,
                (
                    f_data,
                    l_data,
                ),
            )
            return render_template(
                "usl.html",
                f_data=f_data,
                l_data=l_data,
                fdb_reservations_paid=fdb_reservations_paid,
                fdb_reservations_accured=fdb_reservations_accured,
                title="услуги",
                **context
            )
    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()


@app.route("/room_landing", methods=["POST", "GET"])
def room_landing():
    """
    ЗАЕТИ ПОМЕЩЕНИЯ ЗА ПЕРИОДА
    """
    if session.get("logged_in"):
        # action = "/room_landing"
        title = "Заети стаи"
        if request.method == "GET":
            return redirect(url_for("insertdata"))
        else:
            query = """
            with TABLE1
            as (select
                ROOMS.name as name,
                dogovori.name_cyr as dogovor,
                NAST.ROOM_ID as first
                from NAST
                inner join rooms on rooms.id = nast.room_id
                inner join dogovori on dogovori.id = nast.dogovor_id
                where NAST.CHECK_IN_DATE <= ? and
                      dateadd(NAST.DAYS - 1 day to NAST.CHECK_IN_DATE) >= ? and
                      coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
                      NAST.IS_DELETED = '0' and
                      NAST.DOGOVOR_ID is not null
                group by 1, 2, 3, NAST.CHECK_IN_DATE)
            select TABLE1.name, TABLE1.dogovor, count(TABLE1.first)
            from TABLE1
            group by TABLE1.name, TABLE1.dogovor
            """
            f_data = request.form["fdata"] or str(datetime.today().date())
            l_data = request.form["ldata"] or str(datetime.today().date())
            fdb_room_landing = con_to_firebird(
                query,
                (
                    l_data,
                    f_data,
                ),
            )
            return render_template(
                "room_landing.html",
                f_data=f_data,
                l_data=l_data,
                title=title,
                fdb_room_landing=fdb_room_landing,
                **context
            )
    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()


@app.route("/payment", methods=["POST", "GET"])
def payment():
    if session.get("logged_in"):
        if request.method == "POST":
            query = """
            SELECT
                MAIN.NAME,
                MAIN.FOR_DATE,
            SUM(MAIN.SUMA)
            FROM
                (SELECT
                    SMETKI_EL.DEF_NAST_ID,
                    COALESCE(SMETKI_EL.FOR_DATE, CAST(OPR.DATE_TIME AS DATE)) AS FOR_DATE,
                    ROUND(SMETKI_EL.KOL * SMETKI_EL.SUMA, 2) AS SUMA,
                    COALESCE(USL.NAME_CYR, (SELECT
                            TS_KASA.NAME_CYR
                        FROM
                            TS_SMETKA INNER JOIN TS_KASA ON TS_KASA.ID = TS_SMETKA.TS_KASA_ID
                        WHERE
                            TS_SMETKA.SMETKA_EL_ID = SMETKI_EL.ID)) AS NAME
                FROM
                    ACTIVE_NAST INNER JOIN NAST ON NAST.ID = ACTIVE_NAST.NAST_ID AND DATEADD(DAY, NAST.DAYS, CHECK_IN_DATE) >= CURRENT_DATE
                    INNER JOIN ROOMS ON ROOMS.ID = NAST.ROOM_ID AND UPPER(ROOMS.NAME) = UPPER(?)
                    INNER JOIN SMETKI_EL ON SMETKI_EL.DEF_NAST_ID = NAST.ID
                    INNER JOIN OPR ON OPR.ID = SMETKI_EL.OPR_ID
                    LEFT JOIN PRICE ON PRICE.ID = SMETKI_EL.PRICE_ID
                    LEFT JOIN USL ON USL.ID = PRICE.USL_ID
                WHERE
                    NOT EXISTS(SELECT SMT.ID FROM SMT_PAY_NODE SMT WHERE SMT.SMETKA_EL_ID = SMETKI_EL.ID)
                    ) AS MAIN
            GROUP BY 1,2
            ORDER BY 1,2
            """
            query_get_kasa_name = """select ts_kasa.name_lat from ts_kasa"""
            roomname = request.form["roomsinfo"]
            room_payment = con_to_firebird(query, (roomname.upper(),))
            kasa_name = con_to_firebird(query_get_kasa_name)
            kasa_list = [i[0] for i in kasa_name]
            return render_template(
                "payment.html", roomname=roomname, room_payment=room_payment, kasa_name=kasa_list, **context
            )
        else:
            return render_template("payment.html")

    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()


@app.route("/payment/<string:room_name>/<string:kasa>", methods=["GET", "POST"])
def paymnet_id(room_name, kasa):
    if session.get("logged_in"):
        query_ts_smetka_el = """
        SELECT ts_kits.name_cyr,
        opr.date_time,
        ts_smetka_el.suma
        from smetki_el
        inner join nast on smetki_el.def_nast_id = nast.id
        inner join rooms on rooms.id = nast.room_id
        inner join ts_smetka_el on ts_smetka_el.smetka_el_id = smetki_el.id
        inner join opr on opr.id = smetki_el.opr_id
        inner join ts_kits on ts_kits.id = ts_smetka_el.ts_kit_id
        inner join ts_smetka on ts_smetka.smetka_el_id = smetki_el.id
        inner join ts_kasa on ts_kasa.id = ts_smetka.ts_kasa_id
        where rooms.name = ?
        and  NAST.CHECK_IN_DATE <= (select cast('Now' as date) from rdb$database) AND DATEADD(NAST.DAYS DAY TO NAST.CHECK_IN_DATE) >= (select cast('Now' as date) from rdb$database)
        and ts_kasa.name_lat = ?
        """

        def json_format(name, datetime, price):
            r = {"name": name, "datatime": datetime, "price": price}
            return r

        ts_smetka_el = con_to_firebird(
            query_ts_smetka_el,
            (
                room_name.upper(),
                kasa,
            ),
        )
        data = []
        for i in ts_smetka_el:
            data.append(json_format(str(i[0]), str(i[1])[:-10], str(i[2])))
        return json.dumps(data)

    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()


@app.route("/fak", methods=["GET", "POST"])
def fak():
    """
    УСЛУГИ ПРЕЗ ПЕРИОДА
    """
    if session.get("logged_in") is True:
        # action = "/fak"
        title = "фактури"
        if request.method == "GET":
            return redirect(url_for("insertdata"))
        else:
            q = """
            select FAK.ID, FAK.NUMBER,
            case
                when FAK.FIRMA_ID is null then FAK.MOL
            else FIRMI.NAME_FAK
            end,
            case
                when FAK.TIP = '0' then 'Фактура'
            else 'Кредитно известие'
            end,
            FAK.SUMA, FAK.DDS, FAK.TOTAL, PAY_TIP.NAME_CYR,
            case
                when round(FAK.TOTAL / 1.2, 2) = FAK.SUMA then '20%'
                when round(FAK.TOTAL / 1.09, 2) = FAK.SUMA then '9%'
            else '0%'
            end
            from FAK
            inner join OPR on OPR.ID = FAK.OPR_ID
            left join FIRMI on FIRMI.ID = FAK.FIRMA_ID
            inner join PAY_TIP on PAY_TIP.ID = FAK.V_BROI
            where cast(OPR.DATE_TIME as date) between ? and ?
            """
            f_data = request.form["fdata"] or str(datetime.today().date())
            l_data = request.form["ldata"] or str(datetime.today().date())
            fdb_fakturi = con_to_firebird(
                q,
                (
                    f_data,
                    l_data,
                ),
            )
            return render_template(
                "fak.html", f_data=f_data, l_data=l_data, title=title, fdb_fakturi=fdb_fakturi, **context
            )

    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()


@app.route("/fak/<string:id>", methods=["GET", "POST"])
def fak_detail(id):
    if session.get("logged_in") is True:
        q = """
        select
        fak.number,
        fak_el.text, fak_el.kol, fak_el.cena, fak_el.suma_dds, fak_el.suma_total, dds_stavka.dds
        from fak_el
        inner join fak on fak.id = fak_el.fak_id
        inner join dds_stavka on dds_stavka.id = fak_el.dds_id
        where fak.number = ?
        """
        fdb_faktura_detail = con_to_firebird(q, (id,))
        # detail_data = defaultdict(list)

        def json_format(id, name, kol, price, suma_dds, suma_total, dds):
            r = {
                "id": id,
                "name": name,
                "kol": kol,
                "price": price,
                "suma_dds": suma_dds,
                "suma_total": suma_total,
                "dds": dds,
            }
            return r

        d = []
        for i in fdb_faktura_detail:
            d.append(
                json_format(
                    str(i[0]),
                    str(i[1]),
                    str(i[2]),
                    str(i[3]),
                    str(i[4]),
                    str(i[5]),
                    str(i[6]),
                )
            )
        return json.dumps(d)
    else:
        return index()


@app.route("/housekeeping", methods=["GET"])
def housekeeping():
    if session.get("logged_in"):
        # employments = {}
        active_people_and_room = """
        SELECT COUNT(DISTINCT(NAST.room_id)) AS ROOM, COUNT(NAST.ROOM_ID) AS PEOPLE
        FROM ACTIVE_NAST
        INNER JOIN NAST ON NAST.ID = ACTIVE_NAST.nast_id
        where NAST.CHECK_IN_DATE <= current_date and
        dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) >= current_date and
        coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
        NAST.IS_DELETED = '0' and
        NAST.DOGOVOR_ID is not null
        """
        expected_room_and_people = """
        SELECT
        count(distinct(NAST.room_id)) AS ROOM,
        count(NAST.ID) AS PEOPLE
        FROM nast
        where NAST.CHECK_IN_DATE = current_date
        and NAST.IS_DELETED = '0'
        and NAST.last_opr_type <> '101'
        and NAST.DOGOVOR_ID is not null
        and not exists(select active_nast.nast_id from active_nast where nast.id = active_nast.nast_id)
        """
        expected_out_room_and_people = """
        SELECT COUNT(DISTINCT(NAST.room_id)) AS ROOM, COUNT(NAST.ROOM_ID) AS PEOPLE
        FROM ACTIVE_NAST
        INNER JOIN NAST ON NAST.ID = ACTIVE_NAST.nast_id
        where dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) = current_date and
        coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
        NAST.IS_DELETED = '0' and
        NAST.DOGOVOR_ID is not null
        """
        out_of_order = """
        SELECT COUNT(DISTINCT(NAST.room_id)) AS ROOM
        FROM NAST
        where NAST.CHECK_IN_DATE <= current_date and
        dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) >= current_date and
        coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
        NAST.DOGOVOR_ID is null
        """
        dirty_room = """
        SELECT COUNT(*) FROM ROOMS WHERE ROOMS.clear = 0
        """
        # rooms_employment = """
        # with tmp1 as (
        #  select
        #  room_tip.name_cyr as t_type,
        #  rooms.id as not_used,
        #  rooms.room_tip_id as t_count
        #  from room_tip
        #  inner join rooms on rooms.room_tip_id = room_tip.id
        # )
        # select
        # tmp1.t_type,
        # count(tmp1.t_count) as ccc,
        # (SELECT
        #     count(DISTINCT(NAST.room_id)) AS ROOM
        #     FROM nast
        #     where NAST.CHECK_IN_DATE <= current_date and
        #     dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) >= current_date and
        #     coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
        #     NAST.IS_DELETED = '0' and
        #     NAST.DOGOVOR_ID is not null
        #     and nast.room_id = tmp1.not_used
        # ) as tmp_r
        # from tmp1
        # group by 1, tmp1.not_used
        # """
        room = con_to_firebird2(active_people_and_room)
        expected_in = con_to_firebird2(expected_room_and_people)
        expected_out = con_to_firebird2(expected_out_room_and_people)
        out_of_order = con_to_firebird2(out_of_order)
        dirtys = con_to_firebird2(dirty_room)

        return render_template(
            "housekeeping.html",
            room=room[0],
            people=room[1],
            today=datetime.now(),
            expected_room=expected_in[0],
            expected_people=expected_in[1],
            out_room=expected_out[0],
            out_people=expected_out[1],
            out_order=out_of_order[0],
            dirty=dirtys[0],
            # rooms_emps_status=employments
        )
    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()


@app.route("/dirty", methods=["GET"])
def dirty():
    if session.get("logged_in"):
        rooms_status = """
        select
        ROOMS.NAME,
        ROOMS.FLOOR,
        case
        when exists (
            SELECT NAST.room_id AS ROOM
                FROM NAST
                where nast.room_id = rooms.id
                and
                NAST.CHECK_IN_DATE <= current_date and
                dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) >= current_date and
                coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
                NAST.DOGOVOR_ID is null
        ) then 'В ремонт'
        when ROOMS.clear = 1
            THEN 'Почистена'
        else
            case
                when exists (
                    SELECT NAST.room_id AS ROOM
                    FROM ACTIVE_NAST
                    INNER JOIN NAST ON NAST.ID = ACTIVE_NAST.nast_id
                    where nast.room_id = rooms.id
                    and
                    NAST.CHECK_IN_DATE <= current_date and
                    dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) >= current_date and
                    coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
                    NAST.IS_DELETED = '0' and
                    NAST.DOGOVOR_ID is not null
                ) then 'Заета непочистена'
                else
                    'Непочистена'
            end
        end
        FROM ROOMS
        ORDER BY 1
        """
        status = con_to_firebird(rooms_status)
        return render_template("dirty_rooms.html", status=status)
    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()


@app.route('/cart_dirty', methods=['GET'])
def cart_dirty():
    if session.get("logged_in"):
        rooms_status = """
        select
        ROOMS.NAME,
        ROOMS.FLOOR,
        case
        when exists (
            SELECT NAST.room_id AS ROOM
                FROM NAST
                where nast.room_id = rooms.id
                and
                NAST.CHECK_IN_DATE <= current_date and
                dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) >= current_date and
                coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
                NAST.DOGOVOR_ID is null
        ) then 'В ремонт'
        when ROOMS.clear = 1
            THEN 'Почистена'
        else
            case
                when exists (
                    SELECT NAST.room_id AS ROOM
                    FROM ACTIVE_NAST
                    INNER JOIN NAST ON NAST.ID = ACTIVE_NAST.nast_id
                    where nast.room_id = rooms.id
                    and
                    NAST.CHECK_IN_DATE <= current_date and
                    dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) >= current_date and
                    coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
                    NAST.IS_DELETED = '0' and
                    NAST.DOGOVOR_ID is not null
                ) then 'Заета непочистена'
                else
                    'Непочистена'
            end
        end
        FROM ROOMS
        ORDER BY 2
        """
        context = con_to_firebird(rooms_status)
        return render_template('room_cleanup.html', context=context)
    else:
        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()


@app.route('/reservations_card')
def reservations_card():
    if session.get("logged_in") is True:
        query_rooms_names = """select rooms.name, rooms.id from rooms order by 1"""

        query_reserver = """
        select
        rooms.name as rooms,
        nast.check_in_date as check_in,
        dateadd(nast.days -1 day to nast.check_in_date) as check_out,
        nast.reserve_id
        from nast
        inner join rooms on rooms.id = nast.room_id
        inner join reserve on reserve.id = nast.reserve_id
        where nast.check_in_date between CURRENT_DATE and dateadd (30 day to current_date)
        and nast.last_opr_type not in (2, 4, 101)
        and nast.is_deleted = 0
        and nast.id not in (select active_nast.nast_id from active_nast)
        group by 1, 2, 3, 4
        order by 1, 2, 3, 4
        """
        reserve = con_to_firebird(query_reserver)

        data = {}
        for line in reserve:
            room, in_house, out, id_house = line
            in_house = str(in_house.strftime("%d.%m.%Y"))
            out = str(out.strftime("%d.%m.%Y"))
            if room not in data:
                data[room] = []
            data[room].append({'id': id_house, 'in': in_house, 'out': out})

        rooms = con_to_firebird(query_rooms_names)

        # return jsonify(data)
        return render_template('reservations_card.html', rooms=rooms, dates=generate_dates_range(), data=data)
    logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
    return index()


@app.route('/price_change', methods=["GET", "POST"])
def price_change():
    if session.get("logged_in") is True:
        if request.method == "GET":
            return redirect(url_for("insertdata"))
        f_data = request.form["fdata"] or str(datetime.today().date())
        l_data = request.form["ldata"] or str(datetime.today().date())
        query = """
        select
        nast_edit.dt_log,
        rooms.name,
        users.name_cyr,
        nast_edit.old_price,
        nast_edit.new_price
        from nast_edit
        inner join users on users.id = nast_edit.user_id
        inner join nast on nast.id = nast_edit.nast_id
        inner join rooms on rooms.id = nast.room_id
        where cast(nast_edit.dt_log as date) between ? and ?
        and nast_edit.old_price != nast_edit.new_price
        """
        mistake = con_to_firebird(query, (f_data, l_data, ))
        return render_template('price_change.html', mistakes=mistake)

    logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
    return index()


@app.route('/depozit', methods=['GET', 'POST'])
def depozit():
    if session.get("logged_in") is True:
        # query = """
        # select
        # depozit.id,
        # depozit.number,
        # dogovori.name_cyr,
        # depozit.name,
        # payment_el.suma,
        # opr.date_time,
        # case
        # when not exists (select smt_pay_node.payment_el_id from smt_pay_node where smt_pay_node.payment_el_id = payment_el.id)
        # AND NOT EXISTS (SELECT OPR_ANUL.ID FROM OPR_ANUL WHERE OPR_ANUL.AN_OPR_ID = SMETKA.OPR_ID)
        # and not exists (select smetka.opr_id from smetka where opr.opr_tip_id = 33) then 'in'

        # when  EXISTS (SELECT OPR_ANUL.ID FROM OPR_ANUL WHERE OPR_ANUL.AN_OPR_ID = SMETKA.OPR_ID)  then 'storno'

        # when not exists (select smt_pay_node.payment_el_id from smt_pay_node where smt_pay_node.payment_el_id = payment_el.id)
        # AND NOT EXISTS (SELECT OPR_ANUL.ID FROM OPR_ANUL WHERE OPR_ANUL.AN_OPR_ID = SMETKA.OPR_ID)
        # and exists (select opr.opr_tip_id from opr where opr.opr_tip_id = 33) then 'reduce'

        # else 'out'
        # end,
        # cast(dds_stavka.dds as int)
        # from payment_el
        # inner join depozit on depozit.id = payment_el.deposit_id
        # inner join smetka on smetka.id =  payment_el.smetka_id
        # inner join opr on opr.id = smetka.opr_id
        # inner join dogovori on dogovori.id = depozit.dogovor_id
        # inner join dds_stavka on dds_stavka.id = smetka.dds_id
        # where not exists (select old_smt_pay_node.payment_el_id from old_smt_pay_node where old_smt_pay_node.payment_el_id = payment_el.id)
        # order by 1, 6
        # """
        
        # New query has somthing wrong, but execute fast!
        query = """
        select
        distinct payment_el.deposit_id,
        depozit.number,
        dogovori.name_cyr,
        depozit.name,
        dds_stavka.dds,
        SUM(IIF(OPR.OPR_TIP_ID = 10,ROUND(PAYMENT_EL.SUMA,2),0.00)) as income,
        SUM(IIF(OPR.OPR_TIP_ID IN (6,9,33),ROUND(PAYMENT_EL.SUMA,2),0.00)) as outcome
        from payment_el
        INNER JOIN SMETKA ON SMETKA.ID = PAYMENT_EL.SMETKA_ID
        INNER JOIN OPR ON OPR.ID = SMETKA.OPR_ID
        inner join depozit on depozit.id = payment_el.deposit_id
        inner join dogovori on dogovori.id = depozit.dogovor_id
        inner join dds_stavka on dds_stavka.id = smetka.dds_id
        where NOT EXISTS (SELECT OPR_ANUL.OPR_ID FROM OPR_ANUL WHERE OPR_ANUL.AN_OPR_ID = SMETKA.OPR_ID)
        group by 1, 2, 3, 4, 5
        """
        if session.get('logged_in') is True:
            deposits = {}

            result = con_to_firebird(query=query)
            for line in result:
                if line[0] not in deposits:
                    deposits[line[0]] = {'number': line[1], 'contract': line[2], 'from_who': line[3], 'dds': line[4], 'income': line[5], 'outcome': line[6], 'total': line[5] - line[6]}


            return render_template('depozit.html', deposits=deposits)

        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        return index()
    
    logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
    return index()


@app.route('/depozit_detail/<int:dep_id>')
def depozit_detail(dep_id):
    if session.get("logged_in") is True:
        query = """
            select
            depozit.id,
            opr.date_time,
            payment_el.suma,
            case
            when not exists (select smt_pay_node.payment_el_id from smt_pay_node where smt_pay_node.payment_el_id = payment_el.id)
            AND NOT EXISTS (SELECT OPR_ANUL.ID FROM OPR_ANUL WHERE OPR_ANUL.AN_OPR_ID = SMETKA.OPR_ID)
            and not exists (select smetka.opr_id from smetka where opr.opr_tip_id = 33) then 'Зареждане'

            when  EXISTS (SELECT OPR_ANUL.ID FROM OPR_ANUL WHERE OPR_ANUL.AN_OPR_ID = SMETKA.OPR_ID)  then 'storno'

            when not exists (select smt_pay_node.payment_el_id from smt_pay_node where smt_pay_node.payment_el_id = payment_el.id)
            AND NOT EXISTS (SELECT OPR_ANUL.ID FROM OPR_ANUL WHERE OPR_ANUL.AN_OPR_ID = SMETKA.OPR_ID)
            and exists (select opr.opr_tip_id from opr where opr.opr_tip_id = 33) then 'reduce'

            else 'Усвояване'
            end,
            case
            when fak.number is not null then fak.number
            else (
                    select distinct fak.number
                    from smt_pay_node
                    inner join fak on fak.id = smt_pay_node.fak_id
                    where smt_pay_node.payment_el_id = payment_el.id
                )
            end

            from payment_el
            inner join depozit on depozit.id = payment_el.deposit_id
            inner join smetka on smetka.id =  payment_el.smetka_id
            inner join opr on opr.id = smetka.opr_id
            inner join dogovori on dogovori.id = depozit.dogovor_id
            left join fak_deposite_node on fak_deposite_node.smetka_id = smetka.id
            left join fak on fak.id = fak_deposite_node.fak_id
            where not exists (select old_smt_pay_node.payment_el_id from old_smt_pay_node where old_smt_pay_node.payment_el_id = payment_el.id)
            and depozit.id = ?
        """
        fdb_data_smetka_el = con_to_firebird(query, (dep_id,))
        dep_detail = {dep_id: {'time': [], 'opr': [], 'suma': [], 'fak': []}}
        for line in fdb_data_smetka_el:
            dep_detail[dep_id]['time'].append(line[1])
            dep_detail[dep_id]['opr'].append(line[3])
            dep_detail[dep_id]['suma'].append(line[2])
            dep_detail[dep_id]['fak'].append(line[4])
        return dep_detail

    logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
    return index()


@app.route('/otc', methods=["GET", "POST"])
def otc():
    logging.info(f"New income connection from {request.remote_addr} at {datetime.now()}")
    if session.get("logged_in") is True:
        if request.method == "GET":
            return redirect(url_for("insertdata", name='otc'))
        f_data = request.form["fdata"] or str(datetime.today().date())
        l_data = request.form["ldata"] or str(datetime.today().date())
        title = 'otc'
        query = """
        select
        otc_sumi.otc_id,
        otc.otc_date,
        users.name_cyr,
        opr.date_time,
        case
        when otc_sumi.arc=0 and otc_sumi.suma_tip = 0 and otc_sumi.suma_sub_tip = 0 then 'В брой'
        when otc_sumi.arc=0 and otc_sumi.suma_tip = 0 and otc_sumi.suma_sub_tip = 1 then 'По банка'
        when otc_sumi.arc=0 and otc_sumi.suma_tip = 0 and otc_sumi.suma_sub_tip = 2 then 'От Аванс'
        when otc_sumi.arc=0 and otc_sumi.suma_tip = 0 and otc_sumi.suma_sub_tip = 4 then 'Карта'
        when otc_sumi.arc=0 and otc_sumi.suma_tip = 3 and otc_sumi.suma_sub_tip = 4 then 'Тотал'
        when otc_sumi.arc=1 and otc_sumi.suma_tip = 1 and otc_sumi.suma_sub_tip = 1 then 'Нощувки'
        when otc_sumi.arc=1 and otc_sumi.suma_tip = 1 and otc_sumi.suma_sub_tip = 2 then 'Спа'
        when otc_sumi.arc=1 and otc_sumi.suma_tip = 1 and otc_sumi.suma_sub_tip = 3 then 'Пансиони'
        when otc_sumi.arc=1 and otc_sumi.suma_tip = 1 and otc_sumi.suma_sub_tip = 6 then 'Услуги'
        when otc_sumi.arc=1 and otc_sumi.suma_tip = 1 and otc_sumi.suma_sub_tip = 5 then 'Т. обекти'
        when otc_sumi.arc=1 and otc_sumi.suma_tip = 1 and otc_sumi.suma_sub_tip = 9 then 'Усвоен депозит'
        when otc_sumi.arc=1 and otc_sumi.suma_tip = 1 and otc_sumi.suma_sub_tip = 7 then 'Зареждане на аванс'
        else ''
        end,
        otc_sumi.suma
        from otc
        inner join otc_sumi on otc_sumi.otc_id = otc.id
        inner join opr on opr.id = otc.opr_id
        inner join users on users.id = opr.user_id
        where otc.otc_date between ? and ?
        """
        query_result = con_to_firebird(query, (f_data, l_data, ))
        otc = {}
        for line in query_result:
            target = "_".join([str(line[0]), str(line[1]), str(line[2]), str(line[3])])
            if target not in otc:
                otc[target] = {'cash': 0, 'Bank': 0, 'Avans': 0, 'Card': 0, 'Total': 0, 'Nights': 0, 'Spa': 0, 'Pansion': 0, 'Usl': 0, 'TTT': 0, 'UsD': 0, 'IncomeD': 0}
            if line[4].strip() == 'В брой' and otc[target]['cash'] != line[5]:
                otc[target]['cash'] += line[5]
            elif line[4].strip() == 'Карта' and otc[target]['Card'] != line[5]:
                otc[target]['Card'] += line[5]
            elif line[4].strip() == 'По банка' and otc[target]['Bank'] != line[5]:
                otc[target]['Bank'] += line[5]
            elif line[4].strip() == 'От Аванс' and otc[target]['Avans'] != line[5]:
                otc[target]['Avans'] += line[5]
            elif line[4].strip() == 'Тотал' and otc[target]['Total'] != line[5]:
                otc[target]['Total'] += line[5]
            elif line[4].strip() == 'Нощувки' and otc[target]['Nights'] != line[5]:
                otc[target]['Nights'] += line[5]
            elif line[4].strip() == 'Спа' and otc[target]['Spa'] != line[5]:
                otc[target]['Spa'] += line[5]
            elif line[4].strip() == 'Пансиони' and otc[target]['Pansion'] != line[5]:
                otc[target]['Pansion'] += line[5]
            elif line[4].strip() == 'Услуги' and otc[target]['Usl'] != line[5]:
                otc[target]['Usl'] += line[5]
            elif line[4].strip() == 'Т. обекти' and otc[target]['TTT'] != line[5]:
                otc[target]['TTT'] += line[5]
            elif line[4].strip() == 'Усвоен депозит' and otc[target]['UsD'] != line[5]:
                otc[target]['UsD'] += line[5]
            elif line[4].strip() == 'Зареждане на аванс' and otc[target]['IncomeD'] != line[5]:
                otc[target]['IncomeD'] += line[5]

        return render_template('otc.html', otc=otc, title=title, **context)

    logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
    return index()


if __name__ == "__main__":
    app.run(ssl_context=('cert.pem', 'key.pem'), host='0.0.0.0', debug=False)
