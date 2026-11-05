"""HTTP retry safety tests: backoff must respect provider-imposed cooldowns."""
import io
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import collector


class RetryAfterParsingTests(unittest.TestCase):
    def test_numeric_seconds_and_fractions(self):
        self.assertEqual(collector.retry_after_seconds("120"), 120.0)
        self.assertEqual(collector.retry_after_seconds("1.5"), 1.5)
        self.assertEqual(collector.retry_after_seconds("0"), 0.0)

    def test_http_date_and_past_date(self):
        now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(collector.retry_after_seconds("Thu, 05 Nov 2026 12:02:00 GMT", now), 120.0)
        self.assertEqual(collector.retry_after_seconds("Thu, 05 Nov 2026 11:59:00 GMT", now), 0.0)

    def test_bad_or_unbounded_headers_are_ignored(self):
        for value in (None, "", "nonsense", "NaN", "inf", "-inf", "1e999", "Tue, wrong"):
            self.assertIsNone(collector.retry_after_seconds(value), value)
        self.assertEqual(collector.retry_after_seconds("-5"), 0.0)


class RetryRequestTests(unittest.TestCase):
    @staticmethod
    def response():
        return io.BytesIO(b'[]')

    @staticmethod
    def error(status, retry_after=None):
        headers = {} if retry_after is None else {'Retry-After': retry_after}
        return urllib.error.HTTPError("https://api.upbit.com/v1/market/all",
                                      status, "test", headers, None)

    def invoke(self, attempts):
        with patch.object(collector.GATES['upbit'], 'wait') as gate, \
                patch.object(collector.urllib.request, 'urlopen', side_effect=attempts) as urlopen, \
                patch.object(collector.time, 'sleep') as sleep:
            result = collector.request('upbit', '/market/all')
            return result, urlopen.call_count, sleep.call_args_list, gate.call_count

    def test_429_short_retry_after_recovers(self):
        result, calls, sleeps, waits = self.invoke([self.error(429, "2"), self.response()])
        self.assertEqual(result, [])
        self.assertEqual(calls, 2)
        self.assertEqual(waits, 2)
        self.assertEqual(sleeps[0].args, (2.0,))

    def test_http_date_retry_after_above_limit_aborts(self):
        value = (datetime.now(timezone.utc) + timedelta(minutes=2)).strftime("%a, %d %b %Y %H:%M:%S GMT")
        with patch.object(collector.GATES['upbit'], 'wait'), \
                patch.object(collector.urllib.request, 'urlopen', side_effect=self.error(429, value)) as urlopen, \
                patch.object(collector.time, 'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'cooldown'):
                collector.request('upbit', '/market/all')
            self.assertEqual(urlopen.call_count, 1)
            sleep.assert_not_called()

    def test_retry_after_120_aborts_without_second_request(self):
        with patch.object(collector.GATES['upbit'], 'wait'), \
                patch.object(collector.urllib.request, 'urlopen', side_effect=self.error(429, "120")) as urlopen, \
                patch.object(collector.time, 'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'cooldown'):
                collector.request('upbit', '/market/all')
            self.assertEqual(urlopen.call_count, 1)
            sleep.assert_not_called()

    def test_no_retry_after_uses_exponential_backoff(self):
        result, calls, sleeps, _ = self.invoke([self.error(503), self.error(503), self.response()])
        self.assertEqual(result, [])
        self.assertEqual(calls, 3)
        self.assertEqual([x.args for x in sleeps], [(1.0,), (2.0,)])

    def test_non_retryable_http_status_is_not_retried(self):
        with patch.object(collector.GATES['upbit'], 'wait'), \
                patch.object(collector.urllib.request, 'urlopen', side_effect=self.error(403)) as urlopen, \
                patch.object(collector.time, 'sleep') as sleep:
            with self.assertRaises(urllib.error.HTTPError):
                collector.request('upbit', '/market/all')
            self.assertEqual(urlopen.call_count, 1)
            sleep.assert_not_called()

    def test_retryable_code_exhaustion_stops_after_five_attempts(self):
        with patch.object(collector.GATES['upbit'], 'wait'), \
                patch.object(collector.urllib.request, 'urlopen', side_effect=self.error(429, "1")) as urlopen, \
                patch.object(collector.time, 'sleep') as sleep:
            with self.assertRaises(urllib.error.HTTPError):
                collector.request('upbit', '/market/all')
            self.assertEqual(urlopen.call_count, 5)
            self.assertEqual(sleep.call_count, 4)


if __name__ == '__main__':
    unittest.main()
