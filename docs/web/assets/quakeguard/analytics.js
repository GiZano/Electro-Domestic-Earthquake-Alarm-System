// QuakeGuard Google Analytics configuration.
//
// Kept external (instead of an inline snippet) so the page's Content-Security
// Policy can drop 'unsafe-inline' from script-src while Analytics keeps
// working: every gtag(...) call just pushes to the dataLayer queue and the
// loader processes it when the (async) gtag.js bundle arrives.
window.dataLayer = window.dataLayer || [];
function gtag() { dataLayer.push(arguments); }
gtag('js', new Date());
gtag('config', 'G-5JCG2NQS1Y');
