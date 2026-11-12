/* PostHog analytics for smartevguides.com.
   One file for every page: change the token/region here only.
   Named "ph.js" (not "analytics.js") so ad-blocker filename rules don't skip it. */
(function () {
  var POSTHOG_TOKEN = 'phc_ndCsDfYBxsdA5fgvrydw4b3Z57qdQ4MS4ZjHmqGB7QqZ';          // Project settings → Project token (safe to be public)
  var POSTHOG_HOST  = 'https://us.i.posthog.com';  // EU projects: 'https://eu.i.posthog.com'

  // Don't track local previews or an unconfigured token.
  if (POSTHOG_TOKEN.indexOf('REPLACE') !== -1) return;
  if (!/(^|\.)smartevguides\.com$/.test(location.hostname)) return;

  // Official PostHog loader stub (posthog.com/docs/libraries/js)
  !function(t,e){var o,n,p,r;e.__SV||(window.posthog && window.posthog.__loaded)||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}p||((p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",p.onerror=function(){p=null},(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r));var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],Object.defineProperty(u,"toString",{configurable:!0,enumerable:!0,writable:!0,value:function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e}}),Object.defineProperty(u.people,"toString",{configurable:!0,enumerable:!0,writable:!0,value:function(){return u.toString(1)+".people (stub)"}}),o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagResult isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);

  posthog.init(POSTHOG_TOKEN, {
    api_host: POSTHOG_HOST,
    defaults: '2026-08-30',          // pageviews, page-leaves and click autocapture are on by default
    person_profiles: 'identified_only'
  });

  /* Named events for the clicks that matter, so they're one click to chart
     instead of digging through autocapture. Autocapture still records every click. */
  function where(el) {
    var s = el.closest('section[id], header, nav, footer');
    if (!s) return 'page';
    return s.id || s.tagName.toLowerCase();
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var href = a.href, text = (a.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80);
    var props = { link_text: text, link_url: href, location: where(a) };

    if (/apps\.apple\.com/.test(href)) {
      props.store = 'ios';     posthog.capture('app_store_click', props);
    } else if (/play\.google\.com/.test(href)) {
      props.store = 'android'; posthog.capture('app_store_click', props);
    } else if (/^mailto:/i.test(href)) {
      var m = href.match(/[?&]subject=([^&]*)/i);
      props.subject = m ? decodeURIComponent(m[1]) : '';
      posthog.capture('email_click', props);
    } else if (/docs\.google\.com\/forms/.test(href)) {
      posthog.capture('android_signup_form_click', props);
    } else if (a.hostname && a.hostname !== location.hostname) {
      props.domain = a.hostname; posthog.capture('outbound_click', props);
    }
  }, true);
})();
