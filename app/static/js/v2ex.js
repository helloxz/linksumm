// ==UserScript==
// @name         V2EX智能总结
// @namespace    https://linksumm.aimerge.cc
// @version      1.3
// @description  为V2EX帖子添加AI总结功能
// @author       xiaoz
// @match        *://*.v2ex.com/t/*
// @require      https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.min.js
// @require      https://cdn.jsdelivr.net/npm/element-ui@2.15.13/lib/index.js
// @require      https://cdn.jsdelivr.net/npm/axios@0.27.2/dist/axios.min.js
// @require      https://cdn.jsdelivr.net/npm/marked@4.0.18/marked.min.js
// @resource     elementCSS https://cdn.jsdelivr.net/npm/element-ui@2.15.13/lib/theme-chalk/index.css
// @grant        GM_addStyle
// @grant        GM_getResourceText
// @license AGPL-3.0
// ==/UserScript==

(function() {
    'use strict';

    // 添加Element UI和自定义CSS
    const elementCSS = GM_getResourceText('elementCSS');
    const customCSS = GM_getResourceText('customCSS');
    GM_addStyle(elementCSS);
    GM_addStyle(customCSS);
    GM_addStyle(`
    .cell.buttons, .inner.buttons, .topic_buttons{
border-radius:0px;
        }
        .linksumm-container {
            border-radius: 4px;
            padding: 15px;
            background: #f9f9f9;

            border: 1px solid #eaeaea;
        }

        .linksumm-btn {
            margin: 10px 0;
        }

        .linksumm-loading {
            color: #666;
            margin: 10px 0;
        }

        /* 优化结果区域样式 */
        .linksumm-result {
        font-size:14px;
            margin-top: 15px;
            text-align: left; /* 确保左对齐 */
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }

        .linksumm-result p {
            margin: 0.8em 0;
        }

        .linksumm-result h1,
        .linksumm-result h2,
        .linksumm-result h3,
        .linksumm-result h4 {
            margin: 1.2em 0 0.8em;
            color: #222;
        }

        .linksumm-result ul,
        .linksumm-result ol {
            padding-left: 2em;
            margin: 0.8em 0;
        }

        .linksumm-result blockquote {
            border-left: 3px solid #ddd;
            padding-left: 1em;
            margin: 1em 0;
            color: #666;
        }

        .linksumm-result pre {
            background: #f6f8fa;
            padding: 1em;
            border-radius: 3px;
            overflow: auto;
        }

        .linksumm-result code {
            font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            background: rgba(27, 31, 35, 0.05);
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-size: 85%;
        }

        .linksumm-footer {
            margin-top: 1.5em;
            padding-top: 1em;
            border-top: 1px solid #eee;
            font-size: 0.9em;
            color: #999;
            text-align: center;
        }

        .linksumm-footer a {
            color: #409EFF;
            text-decoration: none;
        }

        .linksumm-footer a:hover {
            text-decoration: underline;
        }

        /* 适配V2EX深色模式 */
        .night-mode .linksumm-container {
            background: #2a2a2a;
            border-color: #333;
        }

        .night-mode .linksumm-result {
            color: #ddd;
        }

        .night-mode .linksumm-result h1,
        .night-mode .linksumm-result h2,
        .night-mode .linksumm-result h3,
        .night-mode .linksumm-result h4 {
            color: #eee;
        }

        .night-mode .linksumm-result blockquote {
            border-left-color: #444;
            color: #bbb;
        }

        .night-mode .linksumm-result pre {
            background: #1e1e1e;
        }

        .night-mode .linksumm-result code {
            background: rgba(0, 0, 0, 0.3);
        }

        .night-mode .linksumm-footer {
            border-top-color: #444;
            color: #aaa;
        }
    `);

    // 设备检测函数
    function isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    // 等待页面加载完成
    window.addEventListener('load', function() {
        // 检查是否在帖子页面
        if (!document.querySelector('.content')) return;

        // 创建总结按钮容器
        // 根据设备类型选择不同的选择器
        const headerSelector = isMobileDevice() ? '.content .box' : '.topic_buttons';
        const header = document.querySelector(headerSelector);
        if (!header) return;

        const container = document.createElement('div');
        container.className = 'linksumm-container';
        header.parentNode.insertBefore(container, header.nextSibling);

        // 初始化Vue应用
        const appHTML = `
            <div id="linksumm-app">
                <el-button
                    v-if="showButton"
                    round
                    class="linksumm-btn"
                    type="primary"
                    @click="startSummarization">
                    AI总结
                </el-button>

                <div v-if="isLoading" class="linksumm-loading">
                    正在总结中，请稍候...
                </div>

                <div v-if="errorMessage" class="linksumm-result">
                    <el-alert
                        :title="errorMessage"
                        type="error"
                        show-icon
                        :closable="false">
                    </el-alert>
                </div>

                <div v-if="outputContent" class="linksumm-result">
                    <div v-html="outputContent"></div>
                    <div class="linksumm-footer">
                        由 <a href="https://linksumm.aimerge.cc" target="_blank">LinkSumm</a> 强力驱动
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = appHTML;

        // 配置marked
        marked.setOptions({
            gfm: true,
            breaks: false,
            pedantic: false,
            smartLists: true,
            smartypants: false
        });

        // 初始化Vue
        new Vue({
            el: '#linksumm-app',
            data() {
                return {
                    isLoading: false,
                    errorMessage: '',
                    outputContent: '',
                    summaryContent: '',
                    showButton:true,
                    buttonText: 'AI总结',
                }
            },
            methods: {
                async startSummarization() {
                    if (this.isLoading) return;

                    this.isLoading = true;
                    this.errorMessage = '';
                    this.outputContent = '';
                    this.summaryContent = '';

                    try {
                        // 1. 获取当前页面内容
                        const pageUrl = window.location.href;
                        const pageTitle = document.title;
                        let pageContent = '';

                        // 获取主帖内容
                        const topicContent = document.querySelector('.topic_content');
                        if (topicContent) pageContent += topicContent.textContent + '\n\n';

                        // 获取回复内容
                        const replies = document.querySelectorAll('.reply_content');
                        replies.forEach(reply => {
                            pageContent += reply.textContent + '\n\n';
                        });

                        if (!pageContent.trim()) {
                            throw new Error('无法获取帖子内容');
                        }

                        // 2. 发送到/content接口
                        const formData = new URLSearchParams();
                        formData.append('url', pageUrl);
                        // formData.append('mode', 'fast'); // 使用快速模式
                        // 获取整个页面的HTML内容
                        var htmlContent = document.documentElement.outerHTML;
                        formData.append('html', htmlContent);

                        // const contentResponse = await axios.post('https://linksumm.aimerge.cc/api/get/content', formData);
                        const contentResponse = await axios.post('https://linksumm.aimerge.cc/api/get/html2md', formData);

                        if (contentResponse.data && contentResponse.data.code === 200) {
                            const contentToSummarize = contentResponse.data.data.content;

                            if (!contentToSummarize || contentToSummarize === "No content could be extracted") {
                                throw new Error('无法从页面中提取可读内容');
                            }

                            // 3. 发送到/summ接口进行流式总结
                            await this.fetchSummaryStream(contentToSummarize, pageUrl);

                        } else {
                            throw new Error(contentResponse.data.msg || '获取内容失败');
                        }

                    } catch (error) {
                        this.errorMessage = `错误: ${error.message || '发生未知错误'}`;
                        console.error('总结出错:', error);
                    } finally {
                        this.isLoading = false;
                    }
                },

                async fetchSummaryStream(contentToSummarize, originalUrl) {
                    const payload = {
                        model: 'auto',
                        input: contentToSummarize
                    };

                    try {
                        const response = await fetch('https://linksumm.aimerge.cc/api/summ', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify(payload),
                        });

                        if (!response.ok) {
                            let errorMsg = `网络响应错误 (状态: ${response.status})`;
                            try {
                                const errData = await response.json();
                                errorMsg = errData.msg || errData.detail || errorMsg;
                            } catch(e) { /* 忽略非JSON响应 */ }
                            throw new Error(errorMsg);
                        }

                        // 处理流式响应
                        const reader = response.body.getReader();
                        const decoder = new TextDecoder('utf-8');
                        let buffer = '';

                        while (true) {
                            const { done, value } = await reader.read();
                            if (done) break;

                            buffer += decoder.decode(value, { stream: true });
                            const lines = buffer.split('\n');
                            buffer = lines.pop() || '';

                            for (const line of lines) {
                                if (line.trim() === '' || !line.startsWith('data:')) continue;

                                if (line.includes('[DONE]')) {
                                    await new Promise(resolve => setTimeout(resolve, 50));
                                    break;
                                }

                                try {
                                    const jsonStr = line.substring(5).trim();
                                    const data = JSON.parse(jsonStr);
                                    if (data.value !== undefined) {
                                        this.summaryContent += data.value;
                                        this.outputContent = marked.parse(this.summaryContent);
                                    }
                                } catch (e) {
                                    console.error('解析流数据失败:', line, e);
                                }
                            }

                            if (lines.some(line => line.includes('[DONE]'))) {
                                this.outputContent = marked.parse(this.summaryContent);
                                this.showButton = false;
                                break;
                            }
                        }

                    } catch (error) {
                        console.error('获取或处理总结流失败:', error);
                        throw error;
                    }
                }
            }
        });
    });
})();