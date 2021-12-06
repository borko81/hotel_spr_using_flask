import fdb
from decouple import config

database = {
    "host": f"{config('PATH_TO_BASE')}",
    "database": f"{config('DATABASE_ALIAS')}",
    "user": f"{config('DATABASE_USERNAME')}",
    "password": f"{config('DATABASE_PASSWORD')}",
}


def con_to_firebird(query, *args):
    con = fdb.connect(**database)
    cur = con.cursor()
    try:
        cur.execute(query, *args)
        for line in cur.fetchall():
            yield line
    except fdb.Error as e:
        print(e)
    finally:
        con.close()


def con_to_firebird2(query, *args):
    con = fdb.connect(**database)
    cur = con.cursor()
    try:
        cur.execute(query, *args)
        return cur.fetchone()
    except fdb.Error as e:
        print(e)
    finally:
        con.close()


def con_to_firebird3(query, *args):
    con = fdb.connect(**database)
    cur = con.cursor()
    try:
        cur.execute(query, *args)
        while True:
            rows = cur.fetchmany(500)
            if not rows:
                break
            for line in rows:
                yield line
    except fdb.Error as e:
        print(e)
    finally:
        con.close()


if __name__ == "__main__":
    for line in con_to_firebird(
        """select
    sum((smetki_el.kol * smetki_el.suma)),
    coalesce(usl.name_cyr, 'Търговски обект')
    from SMETKI_EL
    left join price on price.id = smetki_el.price_id
    left join usl on usl.id = price.usl_id
    inner join NAST on NAST.ID = SMETKI_EL.DEF_NAST_ID
    where smetki_el.def_nast_id = ?
    group by usl.name_cyr
    """,
        (9,),
    ):
        print(line)
