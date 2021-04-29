import fdb

database = {
    'host': '192.168.168.12',
	#'database': r'path',
    'user': 'user',
    'password': 'pass'
}


def con_to_firebird(query, *args):
    con = fdb.connect(**database)
    cur = con.cursor()
    try:
        cur.execute(query, *args)
    except fdb.Error as e:
        print(e)
    else:
        for line in cur.fetchall():
            yield line
    finally:
        con.close()


if __name__ == '__main__':
    for line in con_to_firebird('''select
    sum((smetki_el.kol * smetki_el.suma)),
    coalesce(usl.name_cyr, 'Търговски обект')
    from SMETKI_EL
    left join price on price.id = smetki_el.price_id
    left join usl on usl.id = price.usl_id
    inner join NAST on NAST.ID = SMETKI_EL.DEF_NAST_ID
    where smetki_el.def_nast_id = ?
    group by usl.name_cyr
    ''', (9,)):
        print(line)
