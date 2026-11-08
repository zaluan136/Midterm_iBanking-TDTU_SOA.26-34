// Run with playwright-core installed and CHROME_PATH pointing to a Chromium browser.
const { chromium } = require('playwright-core');
const http = require('http');
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const web = path.resolve(__dirname, '../web');
let availableBalance='100', paymentFailure='', paymentPosts=0, accountDelay=0;

const server = http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) {
    let body = {};
    if (req.url === '/api/auth/login') body = {token:'test'};
    else if (req.url === '/api/account/info') {
      body = {full_name:'Test',phone:'0900000000',email:'test@example.com',balance:availableBalance};
      if (accountDelay) return setTimeout(() => {res.setHeader('Content-Type','application/json');res.end(JSON.stringify(body));},accountDelay);
    }
    else if (req.url === '/api/account/transactions') body = [{transaction_code:'previous',tuition_fee_id:2,amount:'10',status:'success',created_at:'2026-01-01'}];
    else if (req.url === '/api/payments/previous') body = {transaction_code:'previous',tuition_fee_id:2,amount:'10',status:'success'};
    else if (req.url === '/api/payments' && req.method === 'POST') {
      paymentPosts++;
      if (paymentFailure) {res.statusCode=409; body={detail:paymentFailure};}
      else body={transaction_code:'test-tx',tuition_fee_id:1,amount:'10',status:'pending_otp',otp_sent:true,email:'t***@example.com'};
    }
    else if (req.url.startsWith('/api/tuition/')) {
      const mssv = decodeURIComponent(req.url.split('/').pop());
      body = [{id:1,mssv,student_name:mssv,semester:'HK1',amount:'10',status:mssv==='PAID'?'paid':'unpaid'}];
      if (mssv === 'OLD') return setTimeout(() => {res.setHeader('Content-Type','application/json'); res.end(JSON.stringify(body));}, 1800);
    }
    res.setHeader('Content-Type','application/json');
    return res.end(JSON.stringify(body));
  }
  const file = req.url === '/' ? 'index.html' : req.url.slice(1);
  if (!['index.html','app.js','app.css'].includes(file)) {res.writeHead(404); return res.end();}
  res.setHeader('Content-Type', file.endsWith('.js') ? 'application/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html');
  fs.createReadStream(path.join(web,file)).pipe(res);
});

(async () => {
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  let browser;
  try {
    browser = await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    await page.locator('[name=username]').first().fill('test');
    await page.locator('[name=password]').first().fill('password');
    await page.locator('#loginForm button').click();
    await page.locator('#workspace').waitFor({state:'visible'});
    const input = page.locator('#lookup [name=mssv]');
    await input.fill('SV001');
    await page.locator('#fees').getByText(/SV001/).waitFor();
    await input.fill('OLD');
    await page.waitForTimeout(700);
    await input.fill('NEW');
    await page.locator('#fees').getByText(/NEW/).waitFor();
    await page.waitForTimeout(2000);
    assert((await page.locator('#fees').innerText()).includes('NEW'));
    assert(!(await page.locator('#fees').innerText()).includes('OLD'));
    await input.fill('');
    assert.strictEqual(await page.locator('#fees').innerText(), '');
    console.log('PASS browser login, automatic lookup, stale response, clearing input');

    await input.fill('PAID');
    await page.locator('#fees').getByText(/PAID/).waitFor();
    assert.strictEqual(await page.locator('#fees button').count(), 0);
    await page.locator('#history').getByRole('button',{name:'Xem / tiếp tục'}).click();
    await page.locator('#paymentResult').getByText(/Thanh toán thành công/).waitFor();
    availableBalance='5';
    await input.fill('LOW');
    await page.locator('#fees').getByText(/LOW/).waitFor();
    accountDelay=1200;
    await page.locator('#fees button').click();
    assert(await page.locator('#payment').isHidden());
    await page.locator('#review').waitFor({state:'visible'});
    accountDelay=0;
    assert(await page.locator('#confirmPayment').isDisabled());
    assert((await page.locator('#reviewMessage').innerText()).includes('không đủ'));
    assert.strictEqual(paymentPosts,0);
    availableBalance='100';
    await input.fill('SV001');
    await page.locator('#fees').getByText(/SV001/).waitFor();
    await page.locator('#fees button').click();
    await page.locator('#confirmPayment').waitFor({state:'visible'});
    await page.waitForFunction(() => !document.querySelector('#confirmPayment').disabled);
    for (const value of ['Test','0900000000','test@example.com','SV001','HK1']) assert((await page.locator('#reviewDetails').innerText()).includes(value));
    assert.strictEqual(paymentPosts,0);
    paymentFailure='Số dư khả dụng không đủ';
    await page.locator('#confirmPayment').click();
    await page.locator('#notice').getByText(/Số dư khả dụng không đủ/).waitFor();
    assert(await page.locator('#review').isHidden());
    await page.locator('#fees button').click();
    paymentFailure='Khoản học phí này đã được thanh toán';
    await page.locator('#confirmPayment').click();
    await page.locator('#notice').getByText(/đã được thanh toán/).waitFor();
    await page.locator('#fees button').click();
    paymentFailure='';
    await page.locator('#confirmPayment').click();
    await page.locator('#payment').waitFor({state:'visible'});
    assert((await page.locator('#paymentResult').innerText()).includes('OTP gửi tới'));
    assert(await page.locator('#review').isHidden());
    console.log('PASS review, paid fee, insufficient funds, stale server data, OTP initiation');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => {console.error(error); process.exitCode=1;});
