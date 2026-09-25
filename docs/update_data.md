# 数据更新指南（以后多打了排位后照做）

目标：把新对局加进数据集 → 重跑分析 → 更新 GitHub。全程约 5 分钟。

---

## 第一步：采集新数据（在自己电脑 Chrome 上）

1. Chrome 打开战绩页 `https://www.wegame.com.cn/helper/valorant/score`，确认已登录
2. 按 `F12` → 点顶部 **Console**
3. 如果提示不能粘贴，先输入 `allow pasting` 回车
4. 粘贴下面整段，回车：

```js
(async () => {
  const api = (name, body) => fetch(
    'https://www.wegame.com.cn/api/v1/wegame.pallas.game.ValBattle/' + name,
    {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}
  ).then(r => r.json());
  const bar = document.createElement('div');
  bar.style.cssText='position:fixed;top:0;left:0;right:0;z-index:999999;background:#2563eb;color:#fff;font:18px sans-serif;padding:12px;text-align:center';
  document.body.appendChild(bar);
  try {
    let list = [], after = null, page = 1;
    while (true) {
      const body = {from_src:'valorant_web', size:11, queueID:'competitive'};
      if (after) body.after = after;
      const r = await api('GetBattleList', body);
      const bs = r.battles || [];
      list = list.concat(bs);
      if (!bs.length) break;
      after = bs[bs.length-1].dtEventTime.replace(/[-: ]/g,'');
      bar.textContent='拉取列表，累计 '+list.length+' 场';
      if (++page > 30) break;
    }
    list = list.filter((b,i,a)=>a.findIndex(x=>x.apEventId===b.apEventId)===i);
    const me = list[0].subject;
    const battles = [];
    for (let i=0; i<list.length; i++) {
      bar.textContent='逐场详情 '+(i+1)+'/'+list.length;
      let mine = null;
      for (let k=0; k<3 && !mine; k++) {
        try {
          const d = await api('GetBattleDetail', {apEventId:list[i].apEventId, from_src:'valorant_web'});
          mine = ((d.battle_detail&&d.battle_detail.players)||[]).find(p=>p.subject===me)||null;
        } catch(e) { await new Promise(r=>setTimeout(r,1200)); }
      }
      battles.push({list:list[i], self_detail:mine});
      await new Promise(r=>setTimeout(r,300));
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify({subject:me,battles})],{type:'application/json'}));
    a.download = 'valorant_details_full.json';
    a.click();
    const ok = battles.filter(x=>x.self_detail).length;
    bar.textContent='✅ 完成！共 '+list.length+' 场，详情成功 '+ok+' 场，文件已下载';
  } catch(e) { bar.textContent='❌ '+e.message; }
})();
```

5. 等顶部蓝条变成「✅ 完成」，浏览器会下载 **valorant_details_full.json**
   - 如果「详情成功 X 场」少于总场数，告诉我，补采即可

## 第二步：更新特工映射（一般不用动）

只有游戏**出新特工**时才需要。在同一 Console 粘：

```js
fetch('https://www.wegame.com.cn/api/v1/wegame.pallas.game.ValBattle/GetChampion',
  {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from_src:'valorant_web'})})
  .then(r=>r.blob()).then(b=>{const a=document.createElement('a');
  a.href=URL.createObjectURL(b);a.download='champions.json';a.click();});
```

新地图同理：出新图后把新代号的中文名告诉我（或自己查 BWIKI），
在 `scripts/02_build_detailed.py` 的 `MAP_NAMES` 里加一行。

## 第三步：交给 Hermes 更新（或自己在服务器跑）

把下载的 `valorant_details_full.json` 发给 Hermes 并说「更新无畏契约项目」，
我会替换原始数据、重跑清洗和分析、推送到 GitHub。

自己动手的话，在仓库目录依次执行：

```bash
# 1. 用新文件替换 data/raw/valorant_details_full.json（出新特工才换 champions.json）
# 2. 重跑全流程
python3 scripts/02_build_detailed.py
python3 scripts/03_analysis.py
# 3. 提交并推送
git add .
git commit -m "更新数据：N场"
git push
```

## 注意事项

- 脚本采集的是**全部**竞技场次，不是增量；所以新文件直接整体替换旧文件即可，不用合并
- 日期更晚的对局会自动排到最前；游戏内战绩页保留全部历史，不用担心旧数据丢失
- 必须在**自己电脑的浏览器**里跑（服务器 IP 过不了登录地校验，错误码 8000102）
- 若脚本中途红字失败：刷新页面重跑即可，数据没下载前不会改动任何文件
