# AI 改完代码你都不知道它为什么那么改，直到我看到这个提示词

## 文章信息

**作者**: Shire AI实验室  
**发布时间**: 2026-05-19 22:06  
**原文链接**: [https://mp.weixin.qq.com/s/r7t7f5GddCNk16sluVp-Mw](https://mp.weixin.qq.com/s/r7t7f5GddCNk16sluVp-Mw)

---

## 正文内容

我要先坦白一件事。

用 Claude Code 写了半年代码之后，我养成了一个特别丢人的习惯。每次 AI 跑完一段代码，我会打开 diff 看一眼。如果改动不超过 30 行，我还能耐着性子一行行看完。超过 50 行，我就直接 approve 了。

不是因为懒。

是因为看不懂。

真的。你让 Claude Code 去重构一个模块，它改了 12 个文件，每个文件里都动了那么几行。你一行一行看过去，每行你都认识，但连在一起你就搞不清它为什么这么改了。你看到一个函数签名变了，你得往前翻三个文件才能找到调用的地方，才能理解它为什么要把参数从两个变成三个。

整个 review 的过程就像在逆向工程一个黑盒。你看到的只是结果，推理过程全靠你自己脑补。改了 50 行，这个脑补大概要 20 分钟。改了 200 行。。。坦率的讲，我不觉得有几个人能耐着性子看完。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/0Wkmjl1rzweamUaFNC5f569s1wDuFvl8kog4QJ4wpGLj8LZ5T7KwicejTTOElnhwX2BcU6ic2wf8Jx7bLLtjkvfxgLxhUibljXJMibyckjTB7ek/640?wx_fmt=png&from=appmsg)

这个痛点，你如果也在用 AI 编程工具，一定懂。

你可能会说，那你就把需求写详细一点呗，把每个边界条件、每种异常情况全写清楚，AI 不就不会乱来了吗？

试过。两个小时写 spec，AI 五分钟就读完了。而且不管你怎么写，总会有你没想到的地方。AI 遇到歧义了，它要么停下来问你，要么自己判断。停下来问你？那你的活就变成了坐在电脑前回答问题，跟当客服没什么区别。自己判断？那就是后面你要 review 的那个痛苦。

那反过来呢？你说「我信任你，放手干吧」。然后 AI 跑了 20 分钟，改了 30 个文件，你打开 diff，血压直接上来了。因为它可能在第 8 个文件里做了一个跟你意图完全不同的架构决策，后面 22 个文件全是基于这个决策展开的。你这时候想改回去，代价是重做一半。

这两种极端，说到底都是同一个问题。AI 在执行过程中做了大量判断，但这些判断对你来说是隐性的。你看到的只有最终的代码变更，推理过程全丢了。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/0Wkmjl1rzwejLps8lodcKvpWBdZKm5UnHETmlCHFzdl7BkAROFNYvnlEv1jR5IQRxuia3gwd4mEvsennI82xGsCut0FNzlibQA9B7q6uE9JZs/640?wx_fmt=png&from=appmsg)

前两天，Claude Code 的核心开发者 Thariq 发了一条推。没有花哨的演示，没有几千字的教程。他就晒了一个自己每天在用的提示词。

原文：implement <SPEC> and while you do, keep a running implementation-notes.html file (or markdown) with decisions you had to make weren't in the spec, things you had to change, tradeoffs you had to make or anything else I should know

就一行。但这一行提示词，解决了我上面说的所有问题。

这个提示词的思路是这样的。你给 AI 一个需求文档，让它去实现。但同时，你让它开一个笔记文件，一边干活一边记笔记。这个笔记不是随便写写的，有四个固定的分类。

第一个，设计决策。你的需求文档里没写清楚的地方，AI 自己做了理解和选择，把选择过程记下来。

第二个，偏离。哪些地方 AI 故意没按你的需求来，为什么没按，理由是什么。这是最危险的一类，因为你最怕的就是 AI 偷偷改了你的意图。现在它必须主动告诉你。

第三个，权衡。AI 还考虑过哪些方案，为什么最终没选。这个分类的精妙之处你可能一下子感受不到。我举个例子。有一次我让 Claude Code 实现一个缓存策略，review 的时候我看到它用了 LRU，我当时心想「为什么不用 LFU？」正准备改，打开笔记一看，它考虑过了，而且写了为什么没用。数据访问模式更符合 LRU 的假设。我不用从头再想一遍。这种感觉，怎么说呢，就像你正准备开口批评一个同事，结果人家已经把他考虑过的所有方案都列出来给你看了。你还批评啥。

第四个，待确认问题。AI 拿不准的地方，标记出来让你集中定夺。不是零散地打断你，而是攒着一起问你。

整个提示词的英文原文我就不贴了，核心逻辑就一句话，让 AI 把实现过程中所有不在你原始需求里的判断，全部记录下来，按这四个维度分类。

就这么简单。

但这四个维度选得太讲究了。

Design decisions 填补的是你 spec 的空白。你的需求文档永远写不完整，这个分类帮 AI 把「它帮你补了哪些脑洞」显性化了。你知道 AI 补了什么，才能判断补得对不对。

Deviations 是最危险也是最关键的。AI 偏离你的需求不可怕，可怕的是你不知道它偏离了。现在它必须告诉你。

Tradeoffs 帮你避免重复思考。你在 review 的时候不用再从头想「这里还有没有更好的方案」，AI 帮你想过了，而且写清楚了理由。

Open questions 是回环点。你不用被零散的问题打断，集中回答一次就行。

![图片](https://mmbiz.qpic.cn/sz_mmbiz_png/0Wkmjl1rzwdTqDCwIdl9OyM9JaiczbSHqWtfXY4o08q18T1VunN2tQz68j1mPgibEyhwibFaKbyMrxsLDFNesKcVOqOfibkv7FgiaTzWdhbiaW9Hc/640?wx_fmt=png&from=appmsg)

说真的，我自己试了之后最大的感受是，这个提示词改变的不是 AI 的能力，而是你和 AI 之间的沟通方式。

它相当于在你们之间建了一层可审计的中间层。AI 依然在自由地做判断，但每个判断都被记录了。你依然在做最终决策，但你有了完整的上下文。以前你是逆向工程 diff，试图从代码变更反推 AI 的思考过程。现在你先看笔记，快速了解 AI 在哪些地方做了什么选择，然后有针对性地去看对应的代码。

效率完全不一样。

我有时候觉得，这个设计最精巧的地方在于它给 AI 提供了一个合法的出口。不是逼它在歧义面前停下来问你，也不是让它闷头瞎猜。而是让它自主推进的同时，把推理过程交出来。AI 不用反复打断你问问题了，你也不用被动的等着审批了。它干它的活，你忙你的事，最后通过这个笔记文件做一次高效的同步。

这是一种管理哲学的转变。从「我要控制你的每一步」到「你自己走，但告诉我你走了哪条路」。

这个道理其实不止适用于 AI 编程。你想想看，你带过一个团队的话，最好的下属不是那个事事来问你请示的人，也不是那个闷头干活什么都不说的人。而是那个自己能做判断，但会及时告诉你他做了什么判断、为什么这么判断的人。

这不就是这个提示词在做的事吗。

回到实际使用这块。我跟你说，我后来在好几个项目里都试了这个方法。效果最明显的是那种需求文档写了一页纸，但实现涉及七八个文件的中等复杂度任务。以前这种任务我最头疼，AI 改完我根本没精力逐行 review。现在多了一层笔记，五分钟就能扫完 AI 做了哪些关键决策，然后重点看那几处就行。

还有一个意外的收获。有时候我看着笔记里的 Tradeoffs 会发现，AI 考虑过的某个被我忽略的方案，其实比我想要的方案更好。这种「原本会被埋没的好想法被救回来了」的感觉，真的太爽了。你以为你在 review AI 的代码，其实 AI 也在 review 你的思路。

![图片](https://mmbiz.qpic.cn/mmbiz_png/0Wkmjl1rzwdA2TKdNxxEficDUb9jw8KgWbNhARSiaCBPp7ZE8xNhpfzpyhFeib85ibacCWLEZ9mpmRI8O7nUnDsoDXdVGiaJ5ceGEH6OrTIPxqB4/640?wx_fmt=png&from=appmsg)

如果你也在用 Claude Code 或者 Codex，我真的建议你试一下这个方法。不用改你的工作流，不用装新工具，不用学什么新框架。就是在你给 AI 的指令后面多加一句话。

让 AI 写日志，不是为了监控它。

是为了理解它。

以上，既然看到这里了，如果觉得不错，随手点个赞、在看、转发三连吧，如果想第一时间收到推送，也可以给我个星标⭐～

谢谢你看我的文章，我们，下次再见。

/ 作者：夏尔AI/ 邮箱：435452239@qq.com


---

## 媒体资源


### 图片 (4)

1. https://mmbiz.qpic.cn/sz_mmbiz_png/0Wkmjl1rzweamUaFNC5f569s1wDuFvl8kog4QJ4wpGLj8LZ5T7KwicejTTOElnhwX2BcU6ic2wf8Jx7bLLtjkvfxgLxhUibljXJMibyckjTB7ek/640?wx_fmt=png&from=appmsg

2. https://mmbiz.qpic.cn/sz_mmbiz_png/0Wkmjl1rzwejLps8lodcKvpWBdZKm5UnHETmlCHFzdl7BkAROFNYvnlEv1jR5IQRxuia3gwd4mEvsennI82xGsCut0FNzlibQA9B7q6uE9JZs/640?wx_fmt=png&from=appmsg

3. https://mmbiz.qpic.cn/sz_mmbiz_png/0Wkmjl1rzwdTqDCwIdl9OyM9JaiczbSHqWtfXY4o08q18T1VunN2tQz68j1mPgibEyhwibFaKbyMrxsLDFNesKcVOqOfibkv7FgiaTzWdhbiaW9Hc/640?wx_fmt=png&from=appmsg

4. https://mmbiz.qpic.cn/mmbiz_png/0Wkmjl1rzwdA2TKdNxxEficDUb9jw8KgWbNhARSiaCBPp7ZE8xNhpfzpyhFeib85ibacCWLEZ9mpmRI8O7nUnDsoDXdVGiaJ5ceGEH6OrTIPxqB4/640?wx_fmt=png&from=appmsg
