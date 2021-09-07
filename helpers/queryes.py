queryes = {
    'active_nast': """
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
    """,
    'active_nast_detail_smt': """
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
        """,
    'list_with_reservations': """
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
            """,
    'reservations_total_room_room_remain': """with table_one as
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
            """,
    'usl_paid': """
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
            """,
    'usl_accuired': """
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
                """,
    'room_landing': """
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
            """,
    'bill': """
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
            """,
    'smetka_el': """
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
            """,
    'all_fak': """
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
            """,
    'fak_detail': """
            select
            fak.number,
            fak_el.text, fak_el.kol, fak_el.cena, fak_el.suma_dds, fak_el.suma_total, dds_stavka.dds
            from fak_el
            inner join fak on fak.id = fak_el.fak_id
            inner join dds_stavka on dds_stavka.id = fak_el.dds_id
            where fak.number = ?
            """,
    'daili_report_active_people_and_room': """
        SELECT COUNT(DISTINCT(NAST.room_id)) AS ROOM, COUNT(NAST.ROOM_ID) AS PEOPLE
            FROM ACTIVE_NAST
            INNER JOIN NAST ON NAST.ID = ACTIVE_NAST.nast_id
            where NAST.CHECK_IN_DATE <= current_date and
            dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) >= current_date and
            coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
            NAST.IS_DELETED = '0' and
            NAST.DOGOVOR_ID is not null""",
    'daili_report_expected_room_and_people': """
            SELECT
            count(distinct(NAST.room_id)) AS ROOM,
            count(NAST.ID) AS PEOPLE
            FROM nast
            where NAST.CHECK_IN_DATE = current_date
            and NAST.IS_DELETED = '0'
            and NAST.last_opr_type <> '101'
            and NAST.DOGOVOR_ID is not null
            and not exists(select active_nast.nast_id from active_nast where nast.id = active_nast.nast_id)
            """,
    'daili_report_expected_out_room_and_people': """
            SELECT COUNT(DISTINCT(NAST.room_id)) AS ROOM, COUNT(NAST.ROOM_ID) AS PEOPLE
            FROM ACTIVE_NAST
            INNER JOIN NAST ON NAST.ID = ACTIVE_NAST.nast_id
            where dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) = current_date and
            coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
            NAST.IS_DELETED = '0' and
            NAST.DOGOVOR_ID is not null
            """,
    'daili_report_out_of_order': """
            SELECT COUNT(DISTINCT(NAST.room_id)) AS ROOM
            FROM NAST
            where NAST.CHECK_IN_DATE <= current_date and
            dateadd(NAST.DAYS day to NAST.CHECK_IN_DATE) >= current_date and
            coalesce(NAST.LAST_OPR_TYPE, 1) in (1, 2, 8, 23, 202) and
            NAST.DOGOVOR_ID is null
            """,
    'daili_report_dirty_room': """SELECT COUNT(*) FROM ROOMS WHERE ROOMS.clear = 0""",
    'rooms_status': """
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
            """,
    'card_dirty': """
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
            """,
    'reservation_in_card': """
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
            """,
    'operator_change_price': """
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
            """,
    'depozits': """
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
            group by 1, 2, 3, 4, 5""",
    'concrete_depozit_detail': """
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
        """,
    'otc': """
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
        """,

}