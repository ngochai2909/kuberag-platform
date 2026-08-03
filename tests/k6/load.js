import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';

const gatewayUrl = (__ENV.KUBERAG_GATEWAY_URL || '').replace(/\/$/, '');
const requestsWithIds = new Counter('rag_responses_with_correlation_ids');
const loadFailures = new Rate('rag_load_failures');

if (!gatewayUrl) {
  throw new Error('KUBERAG_GATEWAY_URL is required, for example http://VM_EXTERNAL_IP:8080');
}

export const options = {
  scenarios: {
    rag_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '35s', target: 1 },
        { duration: '70s', target: 2 },
        { duration: '70s', target: 3 },
        { duration: '35s', target: 0 },
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<55000'],
    rag_load_failures: [
      'rate<0.05',
      { threshold: 'rate<0.20', abortOnFail: true, delayAbortEval: '35s' },
    ],
  },
  tags: { scenario: 'rag-load' },
};

export default function () {
  const response = http.post(
    `${gatewayUrl}/api/v1/query`,
    JSON.stringify({ question: 'Nguon tin nay den tu dau?', top_k: 2 }),
    { headers: { 'Content-Type': 'application/json' }, timeout: '60s' },
  );
  const body = response.json();
  const valid = check(response, {
    'HTTP 200': (r) => r.status === 200,
    'has answer': () => typeof body?.answer === 'string' && body.answer.length > 0,
    'has at least one source': () => Array.isArray(body?.sources) && body.sources.length > 0,
    'has request ID': () => typeof body?.request_id === 'string' && body.request_id.length > 0,
    'has trace ID': () => /^[a-f0-9]{32}$/.test(body?.trace_id || ''),
  });
  loadFailures.add(!valid);
  if (valid) requestsWithIds.add(1);

  // Three VUs with this think time stay below the shared 10 requests/minute
  // Envoy rate limit even while llama.cpp is CPU-bound.
  sleep(35);
}
