import genRaw from '../generator_song_multicam.py?raw'
import utilsRaw from '../multicam_utils.py?raw'
import effectsRaw from '../multicam_effects.py?raw'

let pyodideInstance = null;
let songFile = null;
let effectFile = null;

const consoleOut = document.getElementById('console-output');
const btnGenerate = document.getElementById('btn-generate');
const btnText = document.getElementById('btn-text');

function log(msg) {
  consoleOut.innerHTML += msg + '\n';
  consoleOut.scrollTop = consoleOut.scrollHeight;
}

// Initialize Pyodide
async function initPyodide() {
  try {
    log('Loading Pyodide environment (might take a few seconds)...');
    pyodideInstance = await loadPyodide();
    log('Pyodide loaded successfully.');
    
    // Write python sources to VFS
    pyodideInstance.FS.writeFile('generator_song_multicam.py', genRaw);
    pyodideInstance.FS.writeFile('multicam_utils.py', utilsRaw);
    pyodideInstance.FS.writeFile('multicam_effects.py', effectsRaw);
    
    log('Python modules loaded into Virtual File System.');
    
    // Pre-import modules and patch sys.exit so it doesn't kill Pyodide
    await pyodideInstance.runPythonAsync(`
import sys
import importlib

# Monkey-patch sys.exit to raise a normal RuntimeError instead of SystemExit.
# SystemExit is special-cased by Pyodide and bypasses Python except blocks.
def _web_exit(code=0):
    raise RuntimeError(f"Process exited with code {code}")
sys.exit = _web_exit

# Import the modules now so any import errors surface early
import multicam_utils
import multicam_effects
import generator_song_multicam
print("All modules imported successfully.")
`);
    
    log('Python environment ready.');
    checkReadyState();
  } catch (error) {
    log(`<span style="color:var(--error)">Error loading Pyodide: ${error.message}</span>`);
  }
}

// Setup Dropzones
function setupDropzone(zoneId, inputId, statusId, type) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  const status = document.getElementById(statusId);

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('drag-active');
  });

  zone.addEventListener('dragleave', () => {
    zone.classList.remove('drag-active');
  });

  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-active');
    if (e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0], type, status, zone);
    }
  });

  input.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFile(e.target.files[0], type, status, zone);
    }
  });
}

function handleFile(file, type, statusElem, zoneElem) {
  if (!file.name.endsWith('.json')) {
    alert('Please upload a valid JSON file.');
    return;
  }
  
  if (type === 'song') {
    songFile = file;
  } else {
    effectFile = file;
  }
  
  statusElem.textContent = file.name;
  statusElem.classList.add('loaded');
  zoneElem.classList.add('file-loaded');
  log(`Loaded file: ${file.name}`);
  
  checkReadyState();
}

function checkReadyState() {
  if (pyodideInstance && songFile && effectFile) {
    btnGenerate.disabled = false;
    btnText.textContent = 'Generate & Download ZIP';
  } else {
    btnGenerate.disabled = true;
    if (!pyodideInstance) {
      btnText.textContent = 'Initializing Engine...';
    } else {
      btnText.textContent = 'Waiting for files...';
    }
  }
}

async function runGeneration() {
  btnGenerate.disabled = true;
  btnGenerate.classList.add('loading');
  btnText.textContent = 'Generating...';
  
  try {
    const songText = await songFile.text();
    const effectText = await effectFile.text();
    
    let prefix = document.getElementById('input-name').value.trim();
    if (!prefix) {
      prefix = songFile.name.replace('.json', '');
    }
    
    // Write user files to Pyodide VFS
    pyodideInstance.FS.writeFile('SongScript.json', songText);
    pyodideInstance.FS.writeFile('EffectScript.json', effectText);
    
    log(`\n--- Starting Generation for "${prefix}" ---`);
    
    // Build and run Python code
    // We use pyodideInstance.globals to pass profile_name and read results
    const pyCode = `
import sys
import os
import io
import shutil
import importlib

# Capture stdout
_old_stdout = sys.stdout
sys.stdout = _captured = io.StringIO()

_result_status = "ERROR"
_result_logs = ""

try:
    # Reload modules to pick up fresh state for each run
    import multicam_utils
    import multicam_effects
    import generator_song_multicam
    importlib.reload(multicam_utils)
    importlib.reload(multicam_effects)
    importlib.reload(generator_song_multicam)

    # Re-patch sys.exit after reload (reload restores original references in modules)
    def _web_exit(code=0):
        raise RuntimeError(f"Process exited with code {code}")
    sys.exit = _web_exit

    input_song = 'SongScript.json'
    input_eff = 'EffectScript.json'
    output_dir = 'output'
    profile_name = ${JSON.stringify(prefix)}

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    
    print("Loading EffectScript...")
    from multicam_effects import load_effect_script
    eff_script = load_effect_script(input_eff)
    
    print("Running generator...")
    from generator_song_multicam import generate
    generate(input_song, 3, output_dir, profile_name, eff_script)

    # Zip the output
    print("Compressing output to ZIP...")
    shutil.make_archive("SongMultiCam_Output", 'zip', output_dir)
    print("Done!")
    
    _result_status = "SUCCESS"
except Exception as e:
    import traceback
    print(f"\\nERROR: {e}")
    print(traceback.format_exc())
finally:
    _result_logs = _captured.getvalue()
    sys.stdout = _old_stdout
`;
    
    await pyodideInstance.runPythonAsync(pyCode);
    
    // Read results back from Python globals
    const status = pyodideInstance.globals.get('_result_status');
    const pythonLogs = pyodideInstance.globals.get('_result_logs');
    
    if (pythonLogs) {
      log(pythonLogs);
    }
    
    if (status === "SUCCESS") {
      log(`<span style="color:var(--success)">✅ Generation successful! Preparing download...</span>`);
      
      const zipData = pyodideInstance.FS.readFile('SongMultiCam_Output.zip');
      triggerDownload(zipData, prefix + '_MultiCamera.zip');
      log(`<span style="color:var(--success)">Download triggered.</span>`);
    } else {
      log(`<span style="color:var(--error)">❌ Generation failed. See logs above.</span>`);
    }

  } catch (err) {
    // If Python itself threw (e.g. SystemExit leaked), show the raw error
    log(`<span style="color:var(--error)">Execution error: ${err.message}</span>`);
    
    // Try to recover any captured stdout
    try {
      const partialLogs = pyodideInstance.globals.get('_result_logs');
      if (partialLogs) log(partialLogs);
    } catch (_) { /* ignore */ }
  } finally {
    btnGenerate.disabled = false;
    btnGenerate.classList.remove('loading');
    btnText.textContent = 'Generate & Download ZIP';
  }
}

function triggerDownload(uint8Array, filename) {
  const blob = new Blob([uint8Array], { type: 'application/zip' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  setupDropzone('dropzone-song', 'input-song', 'status-song', 'song');
  setupDropzone('dropzone-effect', 'input-effect', 'status-effect', 'effect');
  
  btnGenerate.addEventListener('click', runGeneration);
  
  initPyodide();
});
