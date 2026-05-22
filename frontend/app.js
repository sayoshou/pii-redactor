window.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("uploadForm");
    const message = document.getElementById("message");
    const fileInput = document.getElementById("fileInput");
    const sensitivityInput = document.getElementById("sensitivity");
    const sensitivityValue = document.getElementById("sensitivityValue");
    const forceSavePicker = document.getElementById("forceSavePicker");
    const saveButton = document.getElementById("saveButton");
    const cancelButton = document.getElementById("cancelButton");
    const progressContainer = document.getElementById("progressContainer");
    const progressBar = document.getElementById("progressBar");
    const progressText = document.getElementById("progressText");
    let pendingBlob = null;
    let pendingFilename = null;
    let abortController = null;

    sensitivityInput.addEventListener("input", () => {
        sensitivityValue.textContent = sensitivityInput.value;
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files && fileInput.files.length > 0) {
            message.textContent = `${fileInput.files[0].name} が選択されました。`;
        }
    });

    function downloadBlob(blob, suggestedName) {
        const downloadUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = suggestedName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(downloadUrl);
    }

    async function saveFile(blob, suggestedName) {
        if (window.showSaveFilePicker) {
            const opts = {
                suggestedName,
                types: [
                    {
                        description: "Redacted file",
                        accept: { "*/*": [`.${suggestedName.split('.').pop()}`] },
                    },
                ],
            };
            try {
                const handle = await window.showSaveFilePicker(opts);
                const writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                return;
            } catch (err) {
                console.warn("showSaveFilePicker failed, falling back to download", err);
            }
        }

        downloadBlob(blob, suggestedName);
    }

    saveButton.addEventListener("click", async () => {
        if (!pendingBlob || !pendingFilename) {
            return;
        }

        try {
            await saveFile(pendingBlob, pendingFilename);
            message.textContent = "保存が完了しました。";
        } catch (err) {
            message.textContent = `保存に失敗しました: ${err.message}`;
        } finally {
            saveButton.hidden = true;
            pendingBlob = null;
            pendingFilename = null;
        }
    });

    cancelButton.addEventListener("click", () => {
        if (abortController) {
            abortController.abort();
            progressContainer.hidden = true;
            cancelButton.hidden = true;
            message.textContent = "処理がキャンセルされました。";
        }
    });

    function updateProgress(percent, status) {
        progressBar.style.width = percent + "%";
        progressText.textContent = status;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!fileInput.files || fileInput.files.length === 0) {
            message.textContent = "ファイルを選択してください。";
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append("file", file);
        formData.append("sensitivity", Number(sensitivityInput.value) / 100);

        progressContainer.hidden = false;
        cancelButton.hidden = false;
        updateProgress(0, "ファイルを解析中…");
        message.textContent = "";

        abortController = new AbortController();

        try {
            setTimeout(() => updateProgress(10, "ファイルをアップロード中…"), 100);
            setTimeout(() => updateProgress(30, "個人情報を検出中…"), 500);
            setTimeout(() => updateProgress(60, "情報を置き換え中…"), 1000);

            const response = await fetch("/api/redact", {
                method: "POST",
                body: formData,
                signal: abortController.signal,
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || "処理に失敗しました");
            }

            updateProgress(90, "ファイルを準備中…");
            const blob = await response.blob();
            const filename = `redacted_${file.name}`;

            updateProgress(100, "完了");
            setTimeout(() => {
                progressContainer.hidden = true;
                cancelButton.hidden = true;
                if (forceSavePicker.checked) {
                    pendingBlob = blob;
                    pendingFilename = filename;
                    saveButton.hidden = false;
                    message.textContent = "処理が完了しました。保存先を指定するには「保存先を指定して保存」ボタンを押してください。";
                } else {
                    saveFile(blob, filename);
                    message.textContent = "完了しました。保存先を指定できました。";
                }
            }, 500);
        } catch (err) {
            if (err.name === "AbortError") {
                message.textContent = "処理がキャンセルされました。";
            } else {
                message.textContent = `エラー: ${err.message}`;
            }
        } finally {
            progressContainer.hidden = true;
            cancelButton.hidden = true;
            abortController = null;
        }
    });
});

