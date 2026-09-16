/* ================= 后台通用脚本 ================= */
layui.use(['layer', 'form', 'element'], function () {
  window.layer = layui.layer;
  window.form = layui.form;
  window.element = layui.element;
});

(function () {
  var meta = document.querySelector('meta[name="csrf-token"]');
  window.CSRF = meta ? meta.getAttribute('content') : '';

  /** 统一请求：默认 POST，自动带 CSRF 头 */
  window.req = function (url, data, method) {
    method = (method || 'POST').toUpperCase();
    var options = {
      method: method,
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRF-Token': window.CSRF,
        'Accept': 'application/json'
      }
    };
    if (method !== 'GET') {
      var fd = new FormData();
      Object.keys(data || {}).forEach(function (key) {
        var value = data[key];
        if (value === undefined || value === null) return;
        if (Array.isArray(value)) {
          value.forEach(function (v) { fd.append(key, v); });
        } else {
          fd.append(key, value);
        }
      });
      options.body = fd;
    }
    return fetch(url, options).then(function (res) {
      return res.json().catch(function () {
        return { code: 500, msg: '服务器返回异常（HTTP ' + res.status + '）' };
      });
    }).catch(function () {
      return { code: 500, msg: '网络异常，请检查服务是否正常运行' };
    });
  };

  window.post = function (url, data) { return window.req(url, data, 'POST'); };

  window.getJson = function (url, params) {
    var qs = new URLSearchParams(params || {}).toString();
    return window.req(url + (qs ? '?' + qs : ''), null, 'GET');
  };

  /** HTML 转义，用于拼接到属性/文本中 */
  window.esc = function (text) {
    if (text === undefined || text === null) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

  /** 提示 */
  window.tip = function (msg, icon) {
    return window.layer.msg(msg, { icon: icon === undefined ? 1 : icon, anim: 6 });
  };

  window.okMsg = function (msg, cb) {
    return window.layer.msg(msg || '操作成功', { icon: 1, time: 1200 }, function () {
      if (typeof cb === 'function') cb();
    });
  };

  window.errMsg = function (msg) {
    return window.layer.msg(msg || '操作失败', { icon: 2, anim: 6 });
  };

  window.confirmDo = function (msg, cb) {
    return window.layer.confirm(msg, {
      title: '操作确认', icon: 3, btn: ['确定', '取消']
    }, function (index) {
      window.layer.close(index);
      cb();
    });
  };

  /** 统一处理接口返回：成功时执行 onSuccess */
  window.handleRes = function (res, onSuccess) {
    if (!res) { window.errMsg('请求失败'); return; }
    if (res.code === 0) {
      if (res.msg) window.tip(res.msg, 1);
      if (typeof onSuccess === 'function') onSuccess(res.data || {});
      return;
    }
    if (res.code === 401) {
      window.errMsg(res.msg || '登录状态已失效');
      setTimeout(function () { window.location.href = '/admin/login'; }, 1200);
      return;
    }
    window.errMsg(res.msg || '操作失败');
  };

  /** 成功后跳转（若接口返回 redirect 则跳转，否则回调） */
  window.handleResOrRedirect = function (res) {
    window.handleRes(res, function (data) {
      if (data && data.redirect) {
        setTimeout(function () { window.location.href = data.redirect; }, 700);
      }
    });
  };

  /** 侧边栏（手机端抽屉） */
  window.toggleSidebar = function () {
    var sidebar = document.querySelector('.admin-sidebar');
    var mask = document.querySelector('.admin-mask');
    if (!sidebar || !mask) return;
    sidebar.classList.toggle('open');
    mask.classList.toggle('show', sidebar.classList.contains('open'));
  };

  document.addEventListener('DOMContentLoaded', function () {
    var mask = document.querySelector('.admin-mask');
    if (mask) mask.addEventListener('click', window.toggleSidebar);

    // 表单回车提交
    document.querySelectorAll('[data-submit-on-enter]').forEach(function (el) {
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          var target = document.querySelector(el.getAttribute('data-submit-on-enter'));
          if (target) target.click();
        }
      });
    });
  });
})();
