import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';

const gatewayUrl = (__ENV.KUBERAG_GATEWAY_URL || '').replace(/\/$/, '');
const rateLimited = new Counter('envoy_rate_limited_responses');
const unexpectedStatus = new Rate('rate_limit_unexpected_status');
const expectedRateLimitStatuses = http.expectedStatuses({ min: 200, max: 299 }, 429);

if (!gatewayUrl) {
  throw new Error('KUBERAG_GATEWAY_URL is required, for example http://VM_EXTERNAL_IP:8080');
}

export const options = {
  // k6 defaults setup() to 60 seconds. The deliberate 65-second quota reset
  // must be allowed to complete before the burst begins.
  setupTimeout: '2m',
  scenarios: {
    rate_limit_burst: {
      executor: 'shared-iterations',
      vus: 15,
      iterations: 15,
      maxDuration: '30s',
      gracefulStop: '0s',
    },
  },
  thresholds: {
    http_req_failed: ['rate==0'],
    rate_limit_unexpected_status: ['rate==0'],
    envoy_rate_limited_responses: ['count>0'],
  },
  tags: { scenario: 'rate-limit' },
};

export function setup() {
  // Do not inherit quota consumed by a preceding smoke/load check. This is a
  // deliberate 65-second wait before the single 15-request burst.
  sleep(Number(__ENV.KUBERAG_RATE_LIMIT_RESET_SECONDS || 65));
}

export default function () {
  const response = http.get(`${gatewayUrl}/api/v1/status`, {
    timeout: '15s',
    // A 429 proves Envoy's limiter worked, so it is an expected response for
    // this scenario. Other 4xx and every 5xx remain failed HTTP requests.
    responseCallback: expectedRateLimitStatuses,
  });
  const accepted = response.status >= 200 && response.status < 300;
  const limited = response.status === 429;
  const valid = accepted || limited;
  check(response, {
    'only 2xx or Envoy 429': () => valid,
    'no 5xx': (r) => r.status < 500,
  });
  unexpectedStatus.add(!valid);
  if (limited) rateLimited.add(1);
}
