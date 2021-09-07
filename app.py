# Import Flask module\s
from flask import Flask, redirect, url_for, render_template, request, session, flash
from firebird.connectfdb import con_to_firebird, con_to_firebird2 

# Import external module's
from collections import defaultdict
import json
import datetime
import time
from datetime import timedelta, datetime
import hashlib
import logging
import os

# Import hekpers
from helpers.helper import get_user_dates_or_return_today
from helpers.queryes import queryes
from helpers.login_wraper import test_login_session_is_ok_or_not

# Configurations ---------------------------------------------------------------------

# Log configuration
logging.basicConfig(filename="logfilename.log", level=logging.DEBUG)


# ПОЛЗВА СЕ ЗА ПРОМЯНА НА ДАТТА ПО НАШИЯ СТАНДАРТ, МОЖЕ ДА СЕ ДОБАВЯТ И ДРУГИ ФОРМАТИ
context = {"now": int(time.time()), "strftime": time.strftime,
           "strptime": datetime.strptime}

# Configure app and config
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
@test_login_session_is_ok_or_not
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
@test_login_session_is_ok_or_not
def info():
    """Списък с настанените гости в списъка гости"""
    action = "/info"
    query = queryes['active_nast']
    fdb_data = con_to_firebird(query)
    return render_template("index.html", action=action, fdb_data=fdb_data, title="гости", **context)


@app.route("/info/<int:guest_id>")
@test_login_session_is_ok_or_not
def detail_info(guest_id):
    """
    ДЕТЕЙЛИТЕ НА СМЕТАТА, ВИКАТ СЕ В МОДАЛНИЯТ ДИАЛОГ
    """
    query = queryes['active_nast_detail_smt']
    fdb_data_smetka_el = con_to_firebird(query, (guest_id,))
    detail_data = {}
    for line in fdb_data_smetka_el:
        detail_data[line[0]] = line[1]
    return detail_data


@app.route("/reservations", methods=["GET", "POST"])
@test_login_session_is_ok_or_not
def reservations():
    """
    СПИСЪК С РЕЗЕРАЦИИ
    """
    # action = "/reservations"
    if request.method == "GET":
        return redirect(url_for("insertdata"))
    else:
        query = queryes['list_with_reservations']
        # Perspectivna zaetost
        q = queryes['reservations_total_room_room_remain']
        
        result = defaultdict(list)
        # End of perp zaetos
        f_data, l_data = get_user_dates_or_return_today()

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


@app.route("/usls", methods=["GET", "POST"])
@test_login_session_is_ok_or_not
def usls():
    """
    НАЧИСЛЕНИ И ПЛАТЕНО УСЛУГИ ЗА ПЕРИДО, ПОЛЗВАТ СЕ 2 КУЕРИТЕ, ЩОТО МИСЛЯ ДА СЕ ДОБАВЯ ОЩЕ!
    """
    if request.method == "GET":
        return redirect(url_for("insertdata"))
    else:
        query_paid = queryes['usl_paid']
        query_accrued = queryes['usl_accuired']
        f_data, l_data = get_user_dates_or_return_today()

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


@app.route("/room_landing", methods=["POST", "GET"])
@test_login_session_is_ok_or_not
def room_landing():
    """
    ЗАЕТИ ПОМЕЩЕНИЯ ЗА ПЕРИОДА
    """
    title = "Заети стаи"
    if request.method == "GET":
        return redirect(url_for("insertdata"))
    else:
        query = queryes['room_landing']
        f_data, l_data = get_user_dates_or_return_today()

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


@app.route("/payment", methods=["POST", "GET"])
@test_login_session_is_ok_or_not
def payment():
    if request.method == "POST":
        query = queryes['bill']
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


@app.route("/payment/<string:room_name>/<string:kasa>", methods=["GET", "POST"])
@test_login_session_is_ok_or_not
def paymnet_id(room_name, kasa):
    query_ts_smetka_el = queryes['smetka_el']

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



@app.route("/fak", methods=["GET", "POST"])
@test_login_session_is_ok_or_not
def fak():
    """
    УСЛУГИ ПРЕЗ ПЕРИОДА
    """
    title = "фактури"
    if request.method == "GET":
        return redirect(url_for("insertdata"))
    else:
        q = queryes['all_fak']
        f_data, l_data = get_user_dates_or_return_today()

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


@app.route("/fak/<string:id>", methods=["GET", "POST"])
@test_login_session_is_ok_or_not
def fak_detail(id):
    q = queryes['fak_detail']
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


@app.route("/housekeeping", methods=["GET"])
@test_login_session_is_ok_or_not
def housekeeping():
    active_people_and_room = queryes['daili_report_active_people_and_room']
    expected_room_and_people = queryes['daili_report_expected_room_and_people']
    expected_out_room_and_people = queryes['daili_report_expected_out_room_and_people']
    out_of_order = queryes['daili_report_out_of_order']
    dirty_room = queryes['daili_report_dirty_room']
    
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
    )


@app.route("/dirty", methods=["GET"])
@test_login_session_is_ok_or_not
def dirty():
    rooms_status = queryes['rooms_status']
    status = con_to_firebird(rooms_status)
    return render_template("dirty_rooms.html", status=status)


@app.route('/cart_dirty', methods=['GET'])
@test_login_session_is_ok_or_not
def cart_dirty():
    rooms_status = queryes['card_dirty']
    context = con_to_firebird(rooms_status)
    return render_template('room_cleanup.html', context=context)


@app.route('/reservations_card')
@test_login_session_is_ok_or_not
def reservations_card():
    query_rooms_names = """select rooms.name, rooms.id from rooms order by 1"""

    query_reserver = queryes['reservation_in_card']
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
    return render_template('reservations_card.html', rooms=rooms, dates=generate_dates_range(), data=data)


@app.route('/price_change', methods=["GET", "POST"])
@test_login_session_is_ok_or_not
def price_change():
    if request.method == "GET":
        return redirect(url_for("insertdata"))

    f_data, l_data = get_user_dates_or_return_today()

    query = queryes['operator_change_price']
    mistake = con_to_firebird(query, (f_data, l_data, ))
    return render_template('price_change.html', mistakes=mistake)


@app.route('/depozit', methods=['GET', 'POST'])
@test_login_session_is_ok_or_not
def depozit():
    query = queryes['depozits']
    deposits = {}

    result = con_to_firebird(query=query)
    for line in result:
        if line[0] not in deposits:
            deposits[line[0]] = {'number': line[1], 'contract': line[2], 'from_who': line[3], 'dds': line[4], 'income': line[5], 'outcome': line[6], 'total': line[5] - line[6]}

    return render_template('depozit.html', deposits=deposits)


@app.route('/depozit_detail/<int:dep_id>')
@test_login_session_is_ok_or_not
def depozit_detail(dep_id):
    """
        Return depozits spr
    """
    query = queryes['concrete_depozit_detail']
    fdb_data_smetka_el = con_to_firebird(query, (dep_id,))
    dep_detail = {dep_id: {'time': [], 'opr': [], 'suma': [], 'fak': []}}
    for line in fdb_data_smetka_el:
        dep_detail[dep_id]['time'].append(line[1])
        dep_detail[dep_id]['opr'].append(line[3])
        dep_detail[dep_id]['suma'].append(line[2])
        dep_detail[dep_id]['fak'].append(line[4])
    return dep_detail


@app.route('/otc', methods=["GET", "POST"])
@test_login_session_is_ok_or_not
def otc():
    """
        Return spr for otc in period
    """
    if request.method == "GET":
        return redirect(url_for("insertdata", name='otc'))

    f_data, l_data = get_user_dates_or_return_today()

    title = 'otc'
    query = queryes['otc']
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



if __name__ == "__main__":
    app.run(ssl_context=('cert.pem', 'key.pem'), host='0.0.0.0', debug=True)
