from datetime import datetime
from pandas.compat import range
import nose
import sys
import numpy as np

from pandas.core.index import Index
from pandas.tseries.index import DatetimeIndex

from pandas import Timestamp
from pandas.tseries.offsets import generate_range
from pandas.tseries.index import cdate_range, bdate_range, date_range

import pandas.core.datetools as datetools
from pandas.util.testing import assertRaisesRegexp
import pandas.util.testing as tm


def _skip_if_windows_python_3():
    if sys.version_info > (3,) and sys.platform == 'win32':
        raise nose.SkipTest("not used on python 3/win32")


def eq_gen_range(kwargs, expected):
    rng = generate_range(**kwargs)
    assert(np.array_equal(list(rng), expected))


START, END = datetime(2009, 1, 1), datetime(2010, 1, 1)


class TestGenRangeGeneration(tm.TestCase):
    def test_generate(self):
        rng1 = list(generate_range(START, END, offset=datetools.bday))
        rng2 = list(generate_range(START, END, time_rule='B'))
        self.assert_numpy_array_equal(rng1, rng2)

    def test_generate_cday(self):
        tm._skip_if_no_cday()
        rng1 = list(generate_range(START, END, offset=datetools.cday))
        rng2 = list(generate_range(START, END, time_rule='C'))
        self.assert_numpy_array_equal(rng1, rng2)

    def test_1(self):
        eq_gen_range(dict(start=datetime(2009, 3, 25), periods=2),
                     [datetime(2009, 3, 25), datetime(2009, 3, 26)])

    def test_2(self):
        eq_gen_range(dict(start=datetime(2008, 1, 1),
                          end=datetime(2008, 1, 3)),
                     [datetime(2008, 1, 1),
                      datetime(2008, 1, 2),
                      datetime(2008, 1, 3)])

    def test_3(self):
        eq_gen_range(dict(start=datetime(2008, 1, 5),
                          end=datetime(2008, 1, 6)),
                     [])


class TestDateRange(tm.TestCase):

    def setUp(self):
        self.rng = bdate_range(START, END)

    def test_constructor(self):
        rng = bdate_range(START, END, freq=datetools.bday)
        rng = bdate_range(START, periods=20, freq=datetools.bday)
        rng = bdate_range(end=START, periods=20, freq=datetools.bday)
        self.assertRaises(ValueError, date_range, '2011-1-1', '2012-1-1', 'B')
        self.assertRaises(ValueError, bdate_range, '2011-1-1', '2012-1-1', 'B')

    def test_naive_aware_conflicts(self):
        naive = bdate_range(START, END, freq=datetools.bday, tz=None)
        aware = bdate_range(START, END, freq=datetools.bday, tz="Asia/Hong_Kong")
        assertRaisesRegexp(TypeError, "tz-naive.*tz-aware", naive.join, aware)
        assertRaisesRegexp(TypeError, "tz-naive.*tz-aware", aware.join, naive)

    def test_cached_range(self):
        rng = DatetimeIndex._cached_range(START, END,
                                          offset=datetools.bday)
        rng = DatetimeIndex._cached_range(START, periods=20,
                                          offset=datetools.bday)
        rng = DatetimeIndex._cached_range(end=START, periods=20,
                                          offset=datetools.bday)

        assertRaisesRegexp(TypeError, "offset", DatetimeIndex._cached_range, START, END)

        assertRaisesRegexp(TypeError, "specify period", DatetimeIndex._cached_range, START,
                          offset=datetools.bday)

        assertRaisesRegexp(TypeError, "specify period", DatetimeIndex._cached_range, end=END,
                          offset=datetools.bday)

        assertRaisesRegexp(TypeError, "start or end", DatetimeIndex._cached_range, periods=20,
                          offset=datetools.bday)

    def test_cached_range_bug(self):
        rng = date_range('2010-09-01 05:00:00', periods=50,
                         freq=datetools.DateOffset(hours=6))
        self.assertEqual(len(rng), 50)
        self.assertEqual(rng[0], datetime(2010, 9, 1, 5))

    def test_timezone_comparaison_bug(self):
        start = Timestamp('20130220 10:00', tz='US/Eastern')
        try:
            date_range(start, periods=2, tz='US/Eastern')
        except AssertionError:
            self.fail()

    def test_timezone_comparaison_assert(self):
        start = Timestamp('20130220 10:00', tz='US/Eastern')
        self.assertRaises(AssertionError, date_range, start, periods=2, tz='Europe/Berlin')

    def test_comparison(self):
        d = self.rng[10]

        comp = self.rng > d
        self.assertTrue(comp[11])
        self.assertFalse(comp[9])

    def test_copy(self):
        cp = self.rng.copy()
        repr(cp)
        self.assertTrue(cp.equals(self.rng))

    def test_repr(self):
        # only really care that it works
        repr(self.rng)

    def test_getitem(self):
        smaller = self.rng[:5]
        self.assert_numpy_array_equal(smaller, self.rng.view(np.ndarray)[:5])
        self.assertEqual(smaller.offset, self.rng.offset)

        sliced = self.rng[::5]
        self.assertEqual(sliced.offset, datetools.bday * 5)

        fancy_indexed = self.rng[[4, 3, 2, 1, 0]]
        self.assertEqual(len(fancy_indexed), 5)
        tm.assert_isinstance(fancy_indexed, DatetimeIndex)
        self.assertIsNone(fancy_indexed.freq)

        # 32-bit vs. 64-bit platforms
        self.assertEqual(self.rng[4], self.rng[np.int_(4)])

    def test_getitem_matplotlib_hackaround(self):
        values = self.rng[:, None]
        expected = self.rng.values[:, None]
        self.assert_numpy_array_equal(values, expected)

    def test_shift(self):
        shifted = self.rng.shift(5)
        self.assertEqual(shifted[0], self.rng[5])
        self.assertEqual(shifted.offset, self.rng.offset)

        shifted = self.rng.shift(-5)
        self.assertEqual(shifted[5], self.rng[0])
        self.assertEqual(shifted.offset, self.rng.offset)

        shifted = self.rng.shift(0)
        self.assertEqual(shifted[0], self.rng[0])
        self.assertEqual(shifted.offset, self.rng.offset)

        rng = date_range(START, END, freq=datetools.bmonthEnd)
        shifted = rng.shift(1, freq=datetools.bday)
        self.assertEqual(shifted[0], rng[0] + datetools.bday)

    def test_pickle_unpickle(self):
        unpickled = self.round_trip_pickle(self.rng)
        self.assertIsNotNone(unpickled.offset)

    def test_union(self):
        # overlapping
        left = self.rng[:10]
        right = self.rng[5:10]

        the_union = left.union(right)
        tm.assert_isinstance(the_union, DatetimeIndex)

        # non-overlapping, gap in middle
        left = self.rng[:5]
        right = self.rng[10:]

        the_union = left.union(right)
        tm.assert_isinstance(the_union, Index)

        # non-overlapping, no gap
        left = self.rng[:5]
        right = self.rng[5:10]

        the_union = left.union(right)
        tm.assert_isinstance(the_union, DatetimeIndex)

        # order does not matter
        self.assert_numpy_array_equal(right.union(left), the_union)

        # overlapping, but different offset
        rng = date_range(START, END, freq=datetools.bmonthEnd)

        the_union = self.rng.union(rng)
        tm.assert_isinstance(the_union, DatetimeIndex)

    def test_outer_join(self):
        # should just behave as union

        # overlapping
        left = self.rng[:10]
        right = self.rng[5:10]

        the_join = left.join(right, how='outer')
        tm.assert_isinstance(the_join, DatetimeIndex)

        # non-overlapping, gap in middle
        left = self.rng[:5]
        right = self.rng[10:]

        the_join = left.join(right, how='outer')
        tm.assert_isinstance(the_join, DatetimeIndex)
        self.assertIsNone(the_join.freq)

        # non-overlapping, no gap
        left = self.rng[:5]
        right = self.rng[5:10]

        the_join = left.join(right, how='outer')
        tm.assert_isinstance(the_join, DatetimeIndex)

        # overlapping, but different offset
        rng = date_range(START, END, freq=datetools.bmonthEnd)

        the_join = self.rng.join(rng, how='outer')
        tm.assert_isinstance(the_join, DatetimeIndex)
        self.assertIsNone(the_join.freq)

    def test_union_not_cacheable(self):
        rng = date_range('1/1/2000', periods=50, freq=datetools.Minute())
        rng1 = rng[10:]
        rng2 = rng[:25]
        the_union = rng1.union(rng2)
        self.assertTrue(the_union.equals(rng))

        rng1 = rng[10:]
        rng2 = rng[15:35]
        the_union = rng1.union(rng2)
        expected = rng[10:]
        self.assertTrue(the_union.equals(expected))

    def test_intersection(self):
        rng = date_range('1/1/2000', periods=50, freq=datetools.Minute())
        rng1 = rng[10:]
        rng2 = rng[:25]
        the_int = rng1.intersection(rng2)
        expected = rng[10:25]
        self.assertTrue(the_int.equals(expected))
        tm.assert_isinstance(the_int, DatetimeIndex)
        self.assertEqual(the_int.offset, rng.offset)

        the_int = rng1.intersection(rng2.view(DatetimeIndex))
        self.assertTrue(the_int.equals(expected))

        # non-overlapping
        the_int = rng[:10].intersection(rng[10:])
        expected = DatetimeIndex([])
        self.assertTrue(the_int.equals(expected))

    def test_intersection_bug(self):
        # GH #771
        a = bdate_range('11/30/2011', '12/31/2011')
        b = bdate_range('12/10/2011', '12/20/2011')
        result = a.intersection(b)
        self.assertTrue(result.equals(b))

    def test_summary(self):
        self.rng.summary()
        self.rng[2:2].summary()

    def test_summary_pytz(self):
        tm._skip_if_no_pytz()
        import pytz
        bdate_range('1/1/2005', '1/1/2009', tz=pytz.utc).summary()

    def test_summary_dateutil(self):
        tm._skip_if_no_dateutil()
        import dateutil
        bdate_range('1/1/2005', '1/1/2009', tz=dateutil.tz.tzutc()).summary()

    def test_misc(self):
        end = datetime(2009, 5, 13)
        dr = bdate_range(end=end, periods=20)
        firstDate = end - 19 * datetools.bday

        assert len(dr) == 20
        assert dr[0] == firstDate
        assert dr[-1] == end

    def test_date_parse_failure(self):
        badly_formed_date = '2007/100/1'

        self.assertRaises(ValueError, Timestamp, badly_formed_date)

        self.assertRaises(ValueError, bdate_range, start=badly_formed_date,
                          periods=10)
        self.assertRaises(ValueError, bdate_range, end=badly_formed_date,
                          periods=10)
        self.assertRaises(ValueError, bdate_range, badly_formed_date,
                          badly_formed_date)

    def test_equals(self):
        self.assertFalse(self.rng.equals(list(self.rng)))

    def test_identical(self):
        t1 = self.rng.copy()
        t2 = self.rng.copy()
        self.assertTrue(t1.identical(t2))

        # name
        t1 = t1.rename('foo')
        self.assertTrue(t1.equals(t2))
        self.assertFalse(t1.identical(t2))
        t2 = t2.rename('foo')
        self.assertTrue(t1.identical(t2))

        # freq
        t2v = Index(t2.values)
        self.assertTrue(t1.equals(t2v))
        self.assertFalse(t1.identical(t2v))

    def test_daterange_bug_456(self):
        # GH #456
        rng1 = bdate_range('12/5/2011', '12/5/2011')
        rng2 = bdate_range('12/2/2011', '12/5/2011')
        rng2.offset = datetools.BDay()

        result = rng1.union(rng2)
        tm.assert_isinstance(result, DatetimeIndex)

    def test_error_with_zero_monthends(self):
        self.assertRaises(ValueError, date_range, '1/1/2000', '1/1/2001',
                          freq=datetools.MonthEnd(0))

    def test_range_bug(self):
        # GH #770
        offset = datetools.DateOffset(months=3)
        result = date_range("2011-1-1", "2012-1-31", freq=offset)

        start = datetime(2011, 1, 1)
        exp_values = [start + i * offset for i in range(5)]
        self.assert_numpy_array_equal(result, DatetimeIndex(exp_values))

    def test_range_tz_pytz(self):
        # GH 2906
        tm._skip_if_no_pytz()
        from pytz import timezone

        tz = timezone('US/Eastern')
        start = tz.localize(datetime(2011, 1, 1))
        end = tz.localize(datetime(2011, 1, 3))

        dr = date_range(start=start, periods=3)
        self.assertEqual(dr.tz.zone, tz.zone)
        self.assertEqual(dr[0], start)
        self.assertEqual(dr[2], end)

        dr = date_range(end=end, periods=3)
        self.assertEqual(dr.tz.zone, tz.zone)
        self.assertEqual(dr[0], start)
        self.assertEqual(dr[2], end)

        dr = date_range(start=start, end=end)
        self.assertEqual(dr.tz.zone, tz.zone)
        self.assertEqual(dr[0], start)
        self.assertEqual(dr[2], end)

    def test_range_tz_dst_straddle_pytz(self):

        tm._skip_if_no_pytz()
        from pytz import timezone
        tz = timezone('US/Eastern')
        dates = [(tz.localize(datetime(2014, 3, 6)),
                  tz.localize(datetime(2014, 3, 12))),
                 (tz.localize(datetime(2013, 11, 1)),
                  tz.localize(datetime(2013, 11, 6)))]
        for (start, end) in dates:
            dr = date_range(start, end, freq='D')
            self.assertEqual(dr[0], start)
            self.assertEqual(dr[-1], end)
            self.assertEqual(np.all(dr.hour==0), True)

            dr = date_range(start, end, freq='D', tz='US/Eastern')
            self.assertEqual(dr[0], start)
            self.assertEqual(dr[-1], end)
            self.assertEqual(np.all(dr.hour==0), True)

            dr = date_range(start.replace(tzinfo=None), end.replace(tzinfo=None), freq='D', tz='US/Eastern')
            self.assertEqual(dr[0], start)
            self.assertEqual(dr[-1], end)
            self.assertEqual(np.all(dr.hour==0), True)

    def test_range_tz_dateutil(self):
        # GH 2906
        tm._skip_if_no_dateutil()
        # Use maybe_get_tz to fix filename in tz under dateutil.
        from pandas.tslib import maybe_get_tz
        tz = lambda x: maybe_get_tz('dateutil/' + x)

        start = datetime(2011, 1, 1, tzinfo=tz('US/Eastern'))
        end = datetime(2011, 1, 3, tzinfo=tz('US/Eastern'))

        dr = date_range(start=start, periods=3)
        self.assertTrue(dr.tz == tz('US/Eastern'))
        self.assertTrue(dr[0] == start)
        self.assertTrue(dr[2] == end)

        dr = date_range(end=end, periods=3)
        self.assertTrue(dr.tz == tz('US/Eastern'))
        self.assertTrue(dr[0] == start)
        self.assertTrue(dr[2] == end)

        dr = date_range(start=start, end=end)
        self.assertTrue(dr.tz == tz('US/Eastern'))
        self.assertTrue(dr[0] == start)
        self.assertTrue(dr[2] == end)

    def test_month_range_union_tz_pytz(self):
        tm._skip_if_no_pytz()
        from pytz import timezone
        tz = timezone('US/Eastern')

        early_start = datetime(2011, 1, 1)
        early_end = datetime(2011, 3, 1)

        late_start = datetime(2011, 3, 1)
        late_end = datetime(2011, 5, 1)

        early_dr = date_range(start=early_start, end=early_end, tz=tz, freq=datetools.monthEnd)
        late_dr = date_range(start=late_start, end=late_end, tz=tz, freq=datetools.monthEnd)

        early_dr.union(late_dr)

    def test_month_range_union_tz_dateutil(self):
        _skip_if_windows_python_3()
        tm._skip_if_no_dateutil()
        from pandas.tslib import _dateutil_gettz as timezone
        tz = timezone('US/Eastern')

        early_start = datetime(2011, 1, 1)
        early_end = datetime(2011, 3, 1)

        late_start = datetime(2011, 3, 1)
        late_end = datetime(2011, 5, 1)

        early_dr = date_range(start=early_start, end=early_end, tz=tz, freq=datetools.monthEnd)
        late_dr = date_range(start=late_start, end=late_end, tz=tz, freq=datetools.monthEnd)

        early_dr.union(late_dr)

    def test_range_closed(self):
        begin = datetime(2011, 1, 1)
        end = datetime(2014, 1, 1)

        for freq in ["3D", "2M", "7W", "3H", "A"]:
            closed = date_range(begin, end, closed=None, freq=freq)
            left = date_range(begin, end, closed="left", freq=freq)
            right = date_range(begin, end, closed="right", freq=freq)

            expected_left = closed[:-1]
            expected_right = closed[1:]

            self.assertTrue(expected_left.equals(left))
            self.assertTrue(expected_right.equals(right))

    def test_years_only(self):
        # GH 6961
        dr = date_range('2014', '2015', freq='M')
        self.assertEqual(dr[0], datetime(2014, 1, 31))
        self.assertEqual(dr[-1], datetime(2014, 12, 31))


class TestCustomDateRange(tm.TestCase):

    def setUp(self):
        tm._skip_if_no_cday()
        self.rng = cdate_range(START, END)

    def test_constructor(self):
        rng = cdate_range(START, END, freq=datetools.cday)
        rng = cdate_range(START, periods=20, freq=datetools.cday)
        rng = cdate_range(end=START, periods=20, freq=datetools.cday)
        self.assertRaises(ValueError, date_range, '2011-1-1', '2012-1-1', 'C')
        self.assertRaises(ValueError, cdate_range, '2011-1-1', '2012-1-1', 'C')

    def test_cached_range(self):
        rng = DatetimeIndex._cached_range(START, END,
                                          offset=datetools.cday)
        rng = DatetimeIndex._cached_range(START, periods=20,
                                          offset=datetools.cday)
        rng = DatetimeIndex._cached_range(end=START, periods=20,
                                          offset=datetools.cday)

        self.assertRaises(Exception, DatetimeIndex._cached_range, START, END)

        self.assertRaises(Exception, DatetimeIndex._cached_range, START,
                          freq=datetools.cday)

        self.assertRaises(Exception, DatetimeIndex._cached_range, end=END,
                          freq=datetools.cday)

        self.assertRaises(Exception, DatetimeIndex._cached_range, periods=20,
                          freq=datetools.cday)

    def test_comparison(self):
        d = self.rng[10]

        comp = self.rng > d
        self.assertTrue(comp[11])
        self.assertFalse(comp[9])

    def test_copy(self):
        cp = self.rng.copy()
        repr(cp)
        self.assertTrue(cp.equals(self.rng))

    def test_repr(self):
        # only really care that it works
        repr(self.rng)

    def test_getitem(self):
        smaller = self.rng[:5]
        self.assert_numpy_array_equal(smaller, self.rng.view(np.ndarray)[:5])
        self.assertEqual(smaller.offset, self.rng.offset)

        sliced = self.rng[::5]
        self.assertEqual(sliced.offset, datetools.cday * 5)

        fancy_indexed = self.rng[[4, 3, 2, 1, 0]]
        self.assertEqual(len(fancy_indexed), 5)
        tm.assert_isinstance(fancy_indexed, DatetimeIndex)
        self.assertIsNone(fancy_indexed.freq)

        # 32-bit vs. 64-bit platforms
        self.assertEqual(self.rng[4], self.rng[np.int_(4)])

    def test_getitem_matplotlib_hackaround(self):
        values = self.rng[:, None]
        expected = self.rng.values[:, None]
        self.assert_numpy_array_equal(values, expected)

    def test_shift(self):
        shifted = self.rng.shift(5)
        self.assertEqual(shifted[0], self.rng[5])
        self.assertEqual(shifted.offset, self.rng.offset)

        shifted = self.rng.shift(-5)
        self.assertEqual(shifted[5], self.rng[0])
        self.assertEqual(shifted.offset, self.rng.offset)

        shifted = self.rng.shift(0)
        self.assertEqual(shifted[0], self.rng[0])
        self.assertEqual(shifted.offset, self.rng.offset)

        rng = date_range(START, END, freq=datetools.bmonthEnd)
        shifted = rng.shift(1, freq=datetools.cday)
        self.assertEqual(shifted[0], rng[0] + datetools.cday)

    def test_pickle_unpickle(self):
        unpickled = self.round_trip_pickle(self.rng)
        self.assertIsNotNone(unpickled.offset)

    def test_union(self):
        # overlapping
        left = self.rng[:10]
        right = self.rng[5:10]

        the_union = left.union(right)
        tm.assert_isinstance(the_union, DatetimeIndex)

        # non-overlapping, gap in middle
        left = self.rng[:5]
        right = self.rng[10:]

        the_union = left.union(right)
        tm.assert_isinstance(the_union, Index)

        # non-overlapping, no gap
        left = self.rng[:5]
        right = self.rng[5:10]

        the_union = left.union(right)
        tm.assert_isinstance(the_union, DatetimeIndex)

        # order does not matter
        self.assert_numpy_array_equal(right.union(left), the_union)

        # overlapping, but different offset
        rng = date_range(START, END, freq=datetools.bmonthEnd)

        the_union = self.rng.union(rng)
        tm.assert_isinstance(the_union, DatetimeIndex)

    def test_outer_join(self):
        # should just behave as union

        # overlapping
        left = self.rng[:10]
        right = self.rng[5:10]

        the_join = left.join(right, how='outer')
        tm.assert_isinstance(the_join, DatetimeIndex)

        # non-overlapping, gap in middle
        left = self.rng[:5]
        right = self.rng[10:]

        the_join = left.join(right, how='outer')
        tm.assert_isinstance(the_join, DatetimeIndex)
        self.assertIsNone(the_join.freq)

        # non-overlapping, no gap
        left = self.rng[:5]
        right = self.rng[5:10]

        the_join = left.join(right, how='outer')
        tm.assert_isinstance(the_join, DatetimeIndex)

        # overlapping, but different offset
        rng = date_range(START, END, freq=datetools.bmonthEnd)

        the_join = self.rng.join(rng, how='outer')
        tm.assert_isinstance(the_join, DatetimeIndex)
        self.assertIsNone(the_join.freq)

    def test_intersection_bug(self):
        # GH #771
        a = cdate_range('11/30/2011', '12/31/2011')
        b = cdate_range('12/10/2011', '12/20/2011')
        result = a.intersection(b)
        self.assertTrue(result.equals(b))

    def test_summary(self):
        self.rng.summary()
        self.rng[2:2].summary()

    def test_summary_pytz(self):
        tm._skip_if_no_pytz()
        import pytz
        cdate_range('1/1/2005', '1/1/2009', tz=pytz.utc).summary()

    def test_summary_dateutil(self):
        tm._skip_if_no_dateutil()
        import dateutil
        cdate_range('1/1/2005', '1/1/2009', tz=dateutil.tz.tzutc()).summary()

    def test_misc(self):
        end = datetime(2009, 5, 13)
        dr = cdate_range(end=end, periods=20)
        firstDate = end - 19 * datetools.cday

        assert len(dr) == 20
        assert dr[0] == firstDate
        assert dr[-1] == end

    def test_date_parse_failure(self):
        badly_formed_date = '2007/100/1'

        self.assertRaises(ValueError, Timestamp, badly_formed_date)

        self.assertRaises(ValueError, cdate_range, start=badly_formed_date,
                          periods=10)
        self.assertRaises(ValueError, cdate_range, end=badly_formed_date,
                          periods=10)
        self.assertRaises(ValueError, cdate_range, badly_formed_date,
                          badly_formed_date)

    def test_equals(self):
        self.assertFalse(self.rng.equals(list(self.rng)))

    def test_daterange_bug_456(self):
        # GH #456
        rng1 = cdate_range('12/5/2011', '12/5/2011')
        rng2 = cdate_range('12/2/2011', '12/5/2011')
        rng2.offset = datetools.CDay()

        result = rng1.union(rng2)
        tm.assert_isinstance(result, DatetimeIndex)

    def test_cdaterange(self):
        rng = cdate_range('2013-05-01', periods=3)
        xp = DatetimeIndex(['2013-05-01', '2013-05-02', '2013-05-03'])
        self.assertTrue(xp.equals(rng))

    def test_cdaterange_weekmask(self):
        rng = cdate_range('2013-05-01', periods=3,
                          weekmask='Sun Mon Tue Wed Thu')
        xp = DatetimeIndex(['2013-05-01', '2013-05-02', '2013-05-05'])
        self.assertTrue(xp.equals(rng))

    def test_cdaterange_holidays(self):
        rng = cdate_range('2013-05-01', periods=3,
                          holidays=['2013-05-01'])
        xp = DatetimeIndex(['2013-05-02', '2013-05-03', '2013-05-06'])
        self.assertTrue(xp.equals(rng))

    def test_cdaterange_weekmask_and_holidays(self):
        rng = cdate_range('2013-05-01', periods=3,
                          weekmask='Sun Mon Tue Wed Thu',
                          holidays=['2013-05-01'])
        xp = DatetimeIndex(['2013-05-02', '2013-05-05', '2013-05-06'])
        self.assertTrue(xp.equals(rng))


if __name__ == '__main__':
    nose.runmodule(argv=[__file__, '-vvs', '-x', '--pdb', '--pdb-failure'],
                   exit=False)
