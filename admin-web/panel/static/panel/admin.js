(function () {
    "use strict";
    const csrf = document.body.dataset.csrf;
    document.querySelectorAll("form[data-confirm]").forEach((form) => form.addEventListener("submit", (event) => {
        if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    }));

    const sidebarToggle = document.getElementById("sidebar-toggle");
    if (sidebarToggle) {
        const setSidebarState = (collapsed) => {
            document.body.classList.toggle("sidebar-collapsed", collapsed);
            sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
            sidebarToggle.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
        };
        setSidebarState(window.localStorage.getItem("sidebar-collapsed") === "true");
        sidebarToggle.addEventListener("click", () => {
            const collapsed = !document.body.classList.contains("sidebar-collapsed");
            setSidebarState(collapsed);
            window.localStorage.setItem("sidebar-collapsed", String(collapsed));
        });
    }

    const editor = document.getElementById("post-editor");
    if (editor) {
        const body = document.getElementById("post-body");
        const info = document.getElementById("media-status");
        const previewTarget = editor.dataset.previewTarget || `post-preview-${Date.now()}`;
        let previewWindow = null;
        let previewTimer = null;
        const submitPreview = () => {
            if (!previewWindow || previewWindow.closed) return;
            const form = document.createElement("form");
            form.method = "POST";
            form.action = editor.dataset.previewUrl;
            form.target = previewTarget;
            form.hidden = true;
            for (const [name, value] of new FormData(editor).entries()) {
                const input = document.createElement("input");
                input.type = "hidden";
                input.name = name;
                input.value = value;
                form.appendChild(input);
            }
            document.body.appendChild(form);
            form.submit();
            form.remove();
        };
        const schedulePreview = () => {
            if (!previewWindow || previewWindow.closed) return;
            window.clearTimeout(previewTimer);
            previewTimer = window.setTimeout(submitPreview, 280);
        };
        document.getElementById("open-post-preview")?.addEventListener("click", () => {
            previewWindow = window.open("about:blank", previewTarget);
            if (!previewWindow) { window.alert("Allow pop-ups for this panel to open the preview."); return; }
            previewWindow.document.title = "Loading preview…";
            submitPreview();
        });
        editor.addEventListener("input", schedulePreview);
        const insertMarkdown = (markdown) => {
            const start = body.selectionStart || body.value.length;
            body.setRangeText(`\n${markdown}\n`, start, body.selectionEnd || start, "end");
            body.focus();
            body.dispatchEvent(new Event("input", {bubbles: true}));
        };
        const uploadImage = async (file) => {
            info.textContent = "validating and uploading…";
            const data = new FormData(); data.append("image", file, file.name || "pasted-image.png");
            const response = await fetch(editor.dataset.mediaUrl, {method: "POST", headers: {"X-CSRFToken": csrf}, body: data});
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Image upload failed.");
            insertMarkdown(result.markdown); info.textContent = "image inserted";
        };
        const media = document.getElementById("media-input");
        media.addEventListener("change", async () => {
            if (!media.files[0]) return;
            try { await uploadImage(media.files[0]); } catch (error) { info.textContent = error.message; }
            media.value = "";
        });
        body.addEventListener("paste", async (event) => {
            const item = [...(event.clipboardData?.items || [])].find((candidate) => candidate.kind === "file" && candidate.type.startsWith("image/"));
            if (!item) return;
            event.preventDefault();
            let file = item.getAsFile();
            if (!file) return;
            const extension = (file.type.split("/")[1] || "png").replace("jpeg", "jpg");
            if (!file.name || file.name === "blob") file = new File([file], `pasted-image-${Date.now()}.${extension}`, {type: file.type});
            try { await uploadImage(file); } catch (error) { info.textContent = error.message; }
        });
        editor.querySelectorAll(".media-choice").forEach((button) => button.addEventListener("click", () => {
            insertMarkdown(button.dataset.markdown);
        }));
        const help = document.querySelector(".markdown-help-wrap");
        const helpButton = document.querySelector(".markdown-help");
        helpButton?.addEventListener("click", () => { const open = help.dataset.open === "true"; help.dataset.open = String(!open); helpButton.setAttribute("aria-expanded", String(!open)); });
        document.addEventListener("keydown", (event) => { if (event.key === "Escape" && help?.dataset.open === "true") { help.dataset.open = "false"; helpButton.setAttribute("aria-expanded", "false"); } });
    }

    const resourceForm = document.getElementById("resources-editor");
    if (resourceForm) {
        let data = JSON.parse(document.getElementById("resources-data").textContent);
        const root = document.getElementById("resource-categories");
        const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
        const id = () => crypto.randomUUID();
        const entryHtml = (entry) => `<div class="entry-card" draggable="true" data-id="${esc(entry.id)}"><span class="drag-handle" title="Drag to reorder">⠿</span><input data-field="title" value="${esc(entry.title)}" placeholder="Title" required><input data-field="url" type="url" value="${esc(entry.url)}" placeholder="https://…" required><input data-field="description" value="${esc(entry.description)}" placeholder="Description"><label class="check"><input data-field="visible" type="checkbox" ${entry.visible ? "checked" : ""}> visible</label><button class="icon-button delete" type="button" data-action="delete-entry" title="Trash entry">×</button></div>`;
        const categoryHtml = (category) => `<section class="category-card" draggable="true" data-id="${esc(category.id)}"><div class="card-head"><span class="drag-handle" title="Drag category">⠿</span><strong>Category</strong><button class="icon-button" type="button" data-action="category-up">↑</button><button class="icon-button" type="button" data-action="category-down">↓</button><button class="icon-button delete" type="button" data-action="delete-category">trash</button></div><div class="category-fields"><input data-field="name" value="${esc(category.name)}" placeholder="Name" required><input data-field="description" value="${esc(category.description)}" placeholder="Description"><label class="color-field">Color<input data-field="color" type="color" value="${esc(category.color || "#71717a")}" title="Category color"></label><label class="check"><input data-field="visible" type="checkbox" ${category.visible ? "checked" : ""}> visible</label></div><div class="entry-list">${category.entries.map(entryHtml).join("")}</div><button class="button small" type="button" data-action="add-entry">Add entry</button></section>`;
        const render = () => { root.innerHTML = data.categories.map(categoryHtml).join(""); };
        const serialize = () => ({
            title: resourceForm.querySelector('[data-resource-root="title"]').value,
            description: resourceForm.querySelector('[data-resource-root="description"]').value,
            categories: [...root.querySelectorAll(":scope > .category-card")].map((category, categoryIndex) => ({
                id: category.dataset.id, name: category.querySelector('[data-field="name"]').value,
                description: category.querySelector('[data-field="description"]').value,
                color: category.querySelector('[data-field="color"]').value,
                visible: category.querySelector('[data-field="visible"]').checked, order: categoryIndex,
                entries: [...category.querySelectorAll(".entry-card")].map((entry, entryIndex) => ({
                    id: entry.dataset.id, title: entry.querySelector('[data-field="title"]').value,
                    url: entry.querySelector('[data-field="url"]').value, description: entry.querySelector('[data-field="description"]').value,
                    visible: entry.querySelector('[data-field="visible"]').checked, order: entryIndex
                }))
            }))
        });
        root.addEventListener("click", (event) => {
            const button = event.target.closest("[data-action]"); if (!button) return;
            const category = button.closest(".category-card"); const entry = button.closest(".entry-card");
            if (button.dataset.action === "add-entry") category.querySelector(".entry-list").insertAdjacentHTML("beforeend", entryHtml({id:id(),title:"",url:"https://",description:"",visible:true}));
            if (button.dataset.action === "delete-entry" && confirm("Move this resource to trash when saved?")) entry.remove();
            if (button.dataset.action === "delete-category" && confirm("Move this category and its entries to trash when saved?")) category.remove();
            if (button.dataset.action === "category-up" && category.previousElementSibling) root.insertBefore(category, category.previousElementSibling);
            if (button.dataset.action === "category-down" && category.nextElementSibling) root.insertBefore(category.nextElementSibling, category);
        });
        root.addEventListener("dragstart", (event) => { const card = event.target.closest(".entry-card,.category-card"); if (card) { card.classList.add("dragging"); event.dataTransfer.effectAllowed = "move"; } });
        root.addEventListener("dragend", (event) => event.target.closest(".entry-card,.category-card")?.classList.remove("dragging"));
        root.addEventListener("dragover", (event) => {
            event.preventDefault(); const dragging = root.querySelector(".dragging"); if (!dragging) return;
            const selector = dragging.classList.contains("entry-card") ? ".entry-card:not(.dragging)" : ":scope > .category-card:not(.dragging)";
            const scope = dragging.classList.contains("entry-card") ? event.target.closest(".entry-list") : root; if (!scope) return;
            const target = event.target.closest(selector); if (target && target.parentElement === scope) scope.insertBefore(dragging, event.clientY < target.getBoundingClientRect().top + target.offsetHeight / 2 ? target : target.nextSibling);
        });
        document.getElementById("add-category").addEventListener("click", () => { data = serialize(); data.categories.push({id:id(),name:"new category",description:"",color:"#71717a",visible:true,entries:[]}); render(); });
        resourceForm.addEventListener("submit", () => { document.getElementById("resources-value").value = JSON.stringify(serialize()); });
        document.getElementById("preview-resources").addEventListener("click", async () => {
            const panel = resourceForm.querySelector(".resource-preview"), frame = document.getElementById("resources-preview"), state = document.getElementById("resources-preview-status");
            panel.hidden = false; state.textContent = "rendering…"; const form = new FormData();
            form.append("resources", JSON.stringify(serialize())); form.append("csrfmiddlewaretoken", csrf);
            try { const response = await fetch(resourceForm.dataset.previewUrl, {method:"POST",body:form}); frame.srcdoc = await response.text(); state.textContent = response.ok ? "preview current" : "preview error"; }
            catch (_) { state.textContent = "preview unavailable"; }
        });
        render();
    }

    class Sha256 {
        constructor(){this.h=new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);this.buf=new Uint8Array(64);this.n=0;this.bytes=0;}
        static K=new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
        update(a){this.bytes+=a.length;let p=0;while(p<a.length){const take=Math.min(64-this.n,a.length-p);this.buf.set(a.subarray(p,p+take),this.n);this.n+=take;p+=take;if(this.n===64){this.block(this.buf);this.n=0;}}return this;}
        block(b){const w=new Uint32Array(64);for(let i=0;i<16;i++)w[i]=(b[i*4]<<24)|(b[i*4+1]<<16)|(b[i*4+2]<<8)|b[i*4+3];for(let i=16;i<64;i++){const x=w[i-15],y=w[i-2],s0=((x>>>7)|(x<<25))^((x>>>18)|(x<<14))^(x>>>3),s1=((y>>>17)|(y<<15))^((y>>>19)|(y<<13))^(y>>>10);w[i]=(w[i-16]+s0+w[i-7]+s1)>>>0;}let [a,c,d,e,f,g,h,j]=this.h;for(let i=0;i<64;i++){const s1=((f>>>6)|(f<<26))^((f>>>11)|(f<<21))^((f>>>25)|(f<<7)),ch=(f&g)^(~f&h),t1=(j+s1+ch+Sha256.K[i]+w[i])>>>0,s0=((a>>>2)|(a<<30))^((a>>>13)|(a<<19))^((a>>>22)|(a<<10)),maj=(a&c)^(a&d)^(c&d),t2=(s0+maj)>>>0;j=h;h=g;g=f;f=(e+t1)>>>0;e=d;d=c;c=a;a=(t1+t2)>>>0;}const v=[a,c,d,e,f,g,h,j];for(let i=0;i<8;i++)this.h[i]=(this.h[i]+v[i])>>>0;}
        hex(){const bits=this.bytes*8;this.buf[this.n++]=0x80;if(this.n>56){this.buf.fill(0,this.n);this.block(this.buf);this.n=0;}this.buf.fill(0,this.n,56);const hi=Math.floor(bits/4294967296),lo=bits>>>0;for(let i=0;i<4;i++){this.buf[56+i]=(hi>>>(24-i*8))&255;this.buf[60+i]=(lo>>>(24-i*8))&255;}this.block(this.buf);return [...this.h].map(x=>x.toString(16).padStart(8,"0")).join("");}
    }
    const uploadForm = document.getElementById("upload-form");
    if (uploadForm) {
        const fileInput=document.getElementById("upload-file"),pathInput=document.getElementById("upload-path"),progress=document.getElementById("upload-progress"),status=document.getElementById("upload-status");
        fileInput.addEventListener("change",()=>{if(fileInput.files[0]&&(!pathInput.value||pathInput.value.endsWith("/")))pathInput.value+=fileInput.files[0].name;});
        document.getElementById("cancel-upload").addEventListener("click", async () => {
            const uploadId=document.getElementById("upload-session").value.trim(); if(!uploadId){status.textContent="Enter an active session ID first.";return;}
            try { const response=await fetch(`${uploadForm.dataset.createUrl}${uploadId}/cancel/`,{method:"POST",headers:{"X-CSRFToken":csrf}}),result=await response.json(); if(!response.ok)throw new Error(result.error); status.textContent="Upload session cancelled."; }
            catch(error){status.textContent=`Cancel failed: ${error.message}`;}
        });
        uploadForm.addEventListener("submit",async(event)=>{event.preventDefault();const file=fileInput.files[0];if(!file)return;try{
            if(new Sha256().update(new TextEncoder().encode("abc")).hex()!=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")throw new Error("Browser SHA-256 self-check failed");
            status.textContent="Calculating SHA-256…";const hasher=new Sha256(),hashChunk=16*1024*1024;for(let offset=0;offset<file.size;offset+=hashChunk){hasher.update(new Uint8Array(await file.slice(offset,offset+hashChunk).arrayBuffer()));progress.value=Math.round((offset+Math.min(hashChunk,file.size-offset))/file.size*15);}const sha256=hasher.hex();
            let uploadId=document.getElementById("upload-session").value.trim(),session;if(uploadId){let response=await fetch(`${uploadForm.dataset.createUrl}${uploadId}/`);session=await response.json();if(!response.ok)throw new Error(session.error||"Resume session not found");if(session.status!=="uploading")throw new Error(`Session is ${session.status}`);if(session.size!==file.size||session.sha256!==sha256)throw new Error("Selected file does not match the resumable session");}else{let response=await fetch(uploadForm.dataset.createUrl,{method:"POST",headers:{"X-CSRFToken":csrf,"Content-Type":"application/json"},body:JSON.stringify({path:pathInput.value,size:file.size,sha256,replace:document.getElementById("upload-replace").checked})});session=await response.json();if(!response.ok)throw new Error(session.error);uploadId=session.id;document.getElementById("upload-session").value=uploadId;}
            const received=new Set(session.received||[]),total=session.totalChunks,indices=[...Array(total).keys()].filter(i=>!received.has(i));let done=received.size;status.textContent=`Uploading ${done}/${total} chunks · session ${uploadId}`;
            const chunkSize=session.chunkSize,worker=async()=>{while(indices.length){const index=indices.shift(),start=index*chunkSize,body=file.slice(start,Math.min(start+chunkSize,file.size));const response=await fetch(`${uploadForm.dataset.createUrl}${uploadId}/chunks/${index}/`,{method:"PUT",headers:{"X-CSRFToken":csrf},body});const result=await response.json();if(!response.ok)throw new Error(result.error);done++;progress.value=15+Math.round(done/total*80);status.textContent=`Uploading ${done}/${total} chunks · session ${uploadId}`;}};await Promise.all([worker(),worker(),worker()]);
            status.textContent="Verifying SHA-256 and publishing…";const response=await fetch(`${uploadForm.dataset.createUrl}${uploadId}/complete/`,{method:"POST",headers:{"X-CSRFToken":csrf}}),result=await response.json();if(!response.ok)throw new Error(result.error);progress.value=100;status.textContent=`Published /src/${result.path}`;
        }catch(error){status.textContent=`Upload stopped: ${error.message}`;}});
    }
})();
