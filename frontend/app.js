// 物流管理系统 · 前端逻辑 / Frontend logic
// 负责：Chi Xuanyi
// 说明：以后接后端接口时用 fetch，例如：
//   fetch('http://localhost:8000/api/orders')
//     .then(r => r.json())
//     .then(data => console.log(data));

document.getElementById('loginBtn').onclick = () => {
  const user = document.getElementById('username').value;
  alert(user ? `欢迎 Welcome, ${user}！` : '请输入用户名 Please enter username');
};
