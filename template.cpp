// 刷题模板 —— 复制这个文件开始写
#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using pii = pair<int, int>;
const int INF = 0x3f3f3f3f;
const ll LINF = 0x3f3f3f3f3f3f3f3fLL;

#define rep(i, a, b) for (int i = (a); i < (b); ++i)
#define all(x) (x).begin(), (x).end()

#ifdef LOCAL
#define debug(x) cerr << #x << " = " << (x) << '\n'
#else
#define debug(x) ((void)0)
#endif

static void solve() {
    int n;
    cin >> n;
    vector<int> a(n);
    for (int &x : a) cin >> x;
    cout << accumulate(a.begin(), a.end(), 0LL) << '\n';
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
#ifdef LOCAL
    // 本地/调试时从 in.txt 读入（配合 .vscode/launch.json 的 gdb 调试）
    freopen("in.txt", "r", stdin);
#endif

    int T = 1;
    // cin >> T;   // 多组数据就取消注释
    while (T--) solve();
    return 0;
}
