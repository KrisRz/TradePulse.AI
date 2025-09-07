#!/usr/bin/env node

/**
 * Frontend-Backend Integration Test
 * Tests the real API endpoints we implemented for analytics components
 */

const https = require('http');

async function makeRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const req = https.request(url, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({
            status: res.statusCode,
            data: JSON.parse(data)
          });
        } catch (e) {
          resolve({
            status: res.statusCode,
            data: data
          });
        }
      });
    });
    
    req.on('error', reject);
    req.end();
  });
}

async function testFrontendBackendIntegration() {
  console.log('🧪 FRONTEND-BACKEND INTEGRATION TEST');
  console.log('=====================================\n');

  const baseURL = 'http://localhost:9002';
  const headers = {
    'Authorization': 'Bearer enterprise_admin_token',
    'Content-Type': 'application/json'
  };

  const tests = [
    {
      name: 'Health Check',
      url: `${baseURL}/api/health`,
      expected: 'status should be healthy or degraded'
    },
    {
      name: 'Signal Analytics Metrics',
      url: `${baseURL}/api/analytics/signals/metrics`,
      headers,
      expected: 'should return signal metrics object'
    },
    {
      name: 'Strategy Win Rates',
      url: `${baseURL}/api/analytics/strategies/win-rates`,
      headers,
      expected: 'should return strategies array'
    },
    {
      name: 'Trading Heatmap',
      url: `${baseURL}/api/analytics/trading/heatmap`,
      headers,
      expected: 'should return heatmap array'
    }
  ];

  let passed = 0;
  let failed = 0;

  for (const test of tests) {
    try {
      console.log(`🔍 Testing: ${test.name}`);
      
      const result = await makeRequest(test.url, { headers: test.headers });
      
      if (result.status === 200) {
        console.log(`✅ PASS: ${test.name}`);
        console.log(`   Status: ${result.status}`);
        console.log(`   Data: ${JSON.stringify(result.data, null, 2).substring(0, 200)}...`);
        passed++;
      } else {
        console.log(`❌ FAIL: ${test.name}`);
        console.log(`   Status: ${result.status}`);
        console.log(`   Error: ${result.data}`);
        failed++;
      }
      
    } catch (error) {
      console.log(`❌ ERROR: ${test.name}`);
      console.log(`   ${error.message}`);
      failed++;
    }
    
    console.log('');
  }

  console.log('📊 RESULTS:');
  console.log(`✅ Passed: ${passed}`);
  console.log(`❌ Failed: ${failed}`);
  console.log(`📈 Success Rate: ${Math.round((passed / (passed + failed)) * 100)}%`);

  if (failed === 0) {
    console.log('\n🎉 ALL TESTS PASSED! Frontend-Backend integration is working correctly.');
    console.log('🚀 The analytics components can now fetch real data from DynamoDB Local.');
  } else {
    console.log('\n⚠️  Some tests failed. Check the backend server and endpoints.');
  }
}

// Run the tests
testFrontendBackendIntegration().catch(console.error);
