const vscode = require('vscode');

exports.run = async function () {
    const psc = process.env.PSC_BIN || '/home/tugatito/Documentos/GitHub/PenguScript/psc/build/psc';
    const file = process.env.PENGU_SMOKE_FILE || '/tmp/psc-f8-smoke.pengu';
    await vscode.workspace.getConfiguration('pengus').update('executablePath', psc, vscode.ConfigurationTarget.Global);
    const ext = vscode.extensions.getExtension('pengus-lang.pengus');
    if (!ext) throw new Error('pengus extension not found');
    await ext.activate();
    const doc = await vscode.workspace.openTextDocument(file);
    await vscode.window.showTextDocument(doc);
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) {
        const diags = vscode.languages.getDiagnostics(doc.uri);
        if (diags.length > 0) {
            console.log('F8_VSCODE_DIAGS=' + JSON.stringify(diags.map(d => ({ message: d.message, source: d.source, severity: d.severity }))));
            return;
        }
        await new Promise(r => setTimeout(r, 300));
    }
    throw new Error('no diagnostics from PenguScript LSP');
};
