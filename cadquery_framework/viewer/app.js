import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';

var EMBEDDED_PARTS = window.__VIEWER_PARTS;
var KICAD_FILES = window.__VIEWER_KICAD;
var EMBEDDED_CONSTRAINTS = window.__VIEWER_CONSTRAINTS;

(function() {
    var container = document.getElementById('canvas-container');
    var scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f5);
    scene.fog = new THREE.Fog(0xf0f0f5, 2000, 8000);

    var cam = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 50000);
    cam.position.set(400, 300, 500);

    var renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.6;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);

    var controls = new OrbitControls(cam, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 1;
    controls.maxDistance = 20000;
    controls.target.set(0, 40, 0);
    controls.update();

    // Lighting
    scene.add(new THREE.AmbientLight(0x606080, 0.8));
    scene.add(new THREE.HemisphereLight(0x8ecae6, 0x6a6a8a, 0.7));
    var keyLight = new THREE.DirectionalLight(0xffffff, 1.0);
    keyLight.position.set(150, 300, 200);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048);
    keyLight.shadow.camera.near = 10; keyLight.shadow.camera.far = 1500;
    keyLight.shadow.camera.left = -500; keyLight.shadow.camera.right = 500;
    keyLight.shadow.camera.top = 500; keyLight.shadow.camera.bottom = -500;
    scene.add(keyLight);
    var fillLight = new THREE.DirectionalLight(0x8ecae6, 0.5);
    fillLight.position.set(-100, 150, -100); scene.add(fillLight);
    var rimLight = new THREE.DirectionalLight(0xffa040, 0.3);
    rimLight.position.set(-50, 50, 200); scene.add(rimLight);
    var underLight = new THREE.DirectionalLight(0xaabbcc, 0.6);
    underLight.position.set(0, -300, 0); scene.add(underLight);
    var underFrontLight = new THREE.DirectionalLight(0x99aacc, 0.4);
    underFrontLight.position.set(100, -200, 150); scene.add(underFrontLight);
    var underRearLight = new THREE.DirectionalLight(0x99aacc, 0.4);
    underRearLight.position.set(-100, -200, -150); scene.add(underRearLight);

    // Grid + ground
    scene.add(new THREE.GridHelper(2000, 100, 0xccccdd, 0xddddee));
    var gnd = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000), new THREE.ShadowMaterial({ opacity: 0.3 }));
    gnd.rotation.x = -Math.PI / 2; gnd.position.y = -0.5; gnd.receiveShadow = true; scene.add(gnd);

    // Axes
    var axH = new THREE.AxesHelper(60);
    axH.position.set(-500, 0, -500); scene.add(axH);
    function mkLabel(t, c, p) {
        var cv = document.createElement('canvas'); cv.width = 64; cv.height = 32;
        var cx = cv.getContext('2d'); cx.fillStyle = c; cx.font = 'bold 24px sans-serif';
        cx.textAlign = 'center'; cx.textBaseline = 'middle'; cx.fillText(t, 32, 16);
        var s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), depthTest: false }));
        s.position.copy(p); s.scale.set(30, 15, 1); return s;
    }
    var axLabels = new THREE.Group();
    axLabels.add(mkLabel('X','#ff4444',new THREE.Vector3(-430,5,-500)));
    axLabels.add(mkLabel('Y','#44ff44',new THREE.Vector3(-500,70,-500)));
    axLabels.add(mkLabel('Z','#4444ff',new THREE.Vector3(-500,5,-430)));
    scene.add(axLabels);

    // Selection
    var selMarker = new THREE.Mesh(
        new THREE.SphereGeometry(2.5, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0xffa040, depthTest: false })
    );
    selMarker.visible = false; selMarker.renderOrder = 999; scene.add(selMarker);
    var highlightedMesh = null;
    var outlineMat = new THREE.MeshBasicMaterial({ color: 0xffa040, wireframe: true, transparent: true, opacity: 0.4 });

    // State
    var parts = {};
    var partOrder = [];
    var selectedPart = null;
    var wireframeOn = false;
    var raycaster = new THREE.Raycaster();
    var mouse = new THREE.Vector2();
    var loader = new STLLoader();

    // TransformControls for part manipulation
    var tfc = new TransformControls(cam, renderer.domElement);
    tfc.setSize(0.8);
    tfc.visible = false;
    tfc.enabled = false;
    scene.add(tfc);
    var transformMode = null;
    var snapEnabled = false;
    var snapGrid = 5;
    var snapAngle = 15;
    var originalTransforms = {};
    var translationDamping = 0.25;
    var translationLastPos = null;

    tfc.addEventListener('dragging-changed', function(e) {
        controls.enabled = !e.value;
        if (e.value && transformMode === 'translate' && selectedPart && parts[selectedPart]) {
            translationLastPos = parts[selectedPart].group.position.clone();
        }
        if (!e.value) translationLastPos = null;
    });
    tfc.addEventListener('change', function() {
        if (!selectedPart || !parts[selectedPart]) return;
        var p = parts[selectedPart];
        var group = p.group;
        if (transformMode === 'translate' && translationLastPos) {
            var rawPos = group.position.clone();
            var delta = rawPos.clone().sub(translationLastPos);
            delta.multiplyScalar(translationDamping);
            translationLastPos.add(delta);
            group.position.copy(translationLastPos);
        }
        var mesh = p.mesh;
        if (highlightedMesh) {
            highlightedMesh.position.copy(mesh.position);
            highlightedMesh.rotation.copy(mesh.rotation);
            highlightedMesh.scale.copy(mesh.scale);
        }
        controls.target.copy(group.position);
        updateTransformFields(p);
    });

    function updateTransformFields(p) {
        if (!p || !p.group) return;
        var group = p.group;
        var d = THREE.MathUtils.radToDeg;
        document.getElementById('tf-px').value = group.position.x.toFixed(1);
        document.getElementById('tf-py').value = group.position.y.toFixed(1);
        document.getElementById('tf-pz').value = group.position.z.toFixed(1);
        document.getElementById('tf-rx').value = d(group.rotation.x).toFixed(1);
        document.getElementById('tf-ry').value = d(group.rotation.y).toFixed(1);
        document.getElementById('tf-rz').value = d(group.rotation.z).toFixed(1);
    }

    function setTransformMode(mode) {
        if (!selectedPart || !parts[selectedPart]) return;
        if (transformMode === mode) {
            tfc.detach();
            tfc.visible = false;
            tfc.enabled = false;
            transformMode = null;
            document.getElementById('btn-move').classList.remove('btn-active-move');
            document.getElementById('btn-rotate').classList.remove('btn-active-rotate');
            return;
        }
        transformMode = mode;
        tfc.setMode(mode);
        var group = parts[selectedPart].group;
        if (mode === 'translate') translationLastPos = group.position.clone();
        tfc.attach(group);
        controls.target.copy(group.position);
        tfc.visible = true;
        tfc.enabled = true;
        document.getElementById('btn-move').classList.toggle('btn-active-move', mode === 'translate');
        document.getElementById('btn-rotate').classList.toggle('btn-active-rotate', mode === 'rotate');
    }

    function detachTransform() {
        tfc.detach();
        tfc.visible = false;
        tfc.enabled = false;
        transformMode = null;
        translationLastPos = null;
        document.getElementById('btn-move').classList.remove('btn-active-move');
        document.getElementById('btn-rotate').classList.remove('btn-active-rotate');
    }

    function addPart(name, display, colorHex, geometry, fileSize, meta) {
        // Support 8-digit hex (#RRGGBBAA) for semi-transparent parts
        var alphaVal = 1.0;
        var cleanHex = colorHex;
        if (colorHex.length === 9) {
            cleanHex = colorHex.substring(0, 7);
            alphaVal = parseInt(colorHex.substring(7, 9), 16) / 255.0;
        }
        var color = new THREE.Color(cleanHex).convertSRGBToLinear();
        var matOpts = {
            color: color, metalness: 0.2, roughness: 0.4, clearcoat: 0.3, clearcoatRoughness: 0.2,
            side: THREE.DoubleSide
        };
        if (alphaVal < 0.99) {
            matOpts.transparent = true;
            matOpts.opacity = alphaVal;
            matOpts.depthWrite = false;
        }
        var mat = new THREE.MeshPhysicalMaterial(matOpts);
        var mesh = new THREE.Mesh(geometry, mat);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.userData.partName = name;
        geometry.computeBoundingBox();
        var center = new THREE.Vector3();
        geometry.boundingBox.getCenter(center);
        var group = new THREE.Group();
        group.position.copy(center);
        mesh.position.set(-center.x, -center.y, -center.z);
        group.add(mesh);
        scene.add(group);
        parts[name] = { group: group, mesh: mesh, geometry: geometry, fileSize: fileSize, color: colorHex, display: display, visible: true, meta: meta || {} };
        originalTransforms[name] = { pos: group.position.clone(), rot: group.rotation.clone() };
        if (partOrder.indexOf(name) === -1) partOrder.push(name);
        updatePartsList();
    }

    function togglePart(name) {
        var p = parts[name];
        if (!p) return;
        p.visible = !p.visible;
        p.group.visible = p.visible;
        if (!p.visible && selectedPart === name) {
            selectedPart = null; clearHighlight(); selMarker.visible = false;
            document.getElementById('selection-panel').style.display = 'none';
            document.getElementById('sel-anchors-toggle').checked = false;
            selectedPartAnchorsOn = false;
            updateAnchorVisibility();
        }
        updatePartsList();
    }

    function clearHighlight() {
        if (highlightedMesh) {
            if (highlightedMesh.parent) highlightedMesh.parent.remove(highlightedMesh);
            highlightedMesh.geometry.dispose();
            highlightedMesh.material.dispose();
            highlightedMesh = null;
        }
    }

    function fitCamera() {
        var box = new THREE.Box3();
        var names = Object.keys(parts);
        if (names.length === 0) return;
        for (var i = 0; i < names.length; i++) {
            var p = parts[names[i]];
            if (!p.visible) continue;
            p.geometry.computeBoundingBox();
            box.union(p.geometry.boundingBox.clone().applyMatrix4(p.mesh.matrixWorld));
        }
        if (box.isEmpty()) return;
        var center = new THREE.Vector3(); box.getCenter(center);
        var size = new THREE.Vector3(); box.getSize(size);
        var dist = Math.max(size.x, size.y, size.z) * 1.8;
        cam.position.set(center.x + dist * 0.6, center.y + dist * 0.4, center.z + dist * 0.7);
        controls.target.copy(center); controls.update();
    }

    function updatePartsList() {
        var c = document.getElementById('parts-container');
        c.innerHTML = '';
        for (var i = 0; i < partOrder.length; i++) {
            var name = partOrder[i];
            var p = parts[name];
            if (!p) continue;
            var div = document.createElement('div');
            div.className = 'part-item' + (selectedPart === name ? ' selected' : '');
            var sizeKB = p.fileSize ? (p.fileSize / 1024).toFixed(1) + ' KB' : '';
            div.innerHTML = '<span class="eye ' + (p.visible ? 'visible' : '') + '" data-part="' + name + '">&#9679;</span>' +
                '<span style="flex:1">' + p.display + '</span><span class="size">' + sizeKB + '</span>';
            div.setAttribute('data-part', name);
            div.addEventListener('click', function(e) {
                if (e.target.classList.contains('eye')) {
                    togglePart(e.target.getAttribute('data-part'));
                } else {
                    selectPart(this.getAttribute('data-part'), null);
                }
            });
            c.appendChild(div);
        }
    }

    function selectPart(name, hitPoint) {
        selectedPart = name;
        var p = parts[name];
        if (!p) return;
        clearHighlight();
        highlightedMesh = new THREE.Mesh(p.geometry.clone(), outlineMat.clone());
        highlightedMesh.position.copy(p.mesh.position);
        highlightedMesh.rotation.copy(p.mesh.rotation);
        highlightedMesh.scale.copy(p.mesh.scale);
        p.group.add(highlightedMesh);

        p.geometry.computeBoundingBox();
        var box = p.geometry.boundingBox.clone().applyMatrix4(p.mesh.matrixWorld);
        var size = new THREE.Vector3(); box.getSize(size);
        var center = new THREE.Vector3(); box.getCenter(center);
        var tris = p.geometry.attributes.position.count / 3;

        document.getElementById('selection-panel').style.display = 'block';
        document.getElementById('sel-title').textContent = p.display;
        var m = p.meta || {};
        document.getElementById('sel-material').textContent = m.material || '-';
        document.getElementById('sel-dims').textContent = m.dims || '-';
        document.getElementById('sel-mass').textContent = m.mass_g ? m.mass_g + 'g' + (m.qty > 1 ? ' each (' + (m.mass_g * m.qty) + 'g total)' : '') : '-';
        document.getElementById('sel-qty').textContent = m.qty ? m.qty + 'x' : '-';
        document.getElementById('sel-supplier').textContent = m.supplier || '-';
        document.getElementById('sel-notes').textContent = m.notes || '-';
        document.getElementById('sel-iface').textContent = m['interface'] || '-';
        document.getElementById('sel-tris').textContent = tris.toLocaleString();
        document.getElementById('sel-fsize').textContent = p.fileSize ? (p.fileSize / 1024).toFixed(1) + ' KB' : '-';
        document.getElementById('sel-bbox').textContent = size.x.toFixed(1) + ' x ' + size.y.toFixed(1) + ' x ' + size.z.toFixed(1) + ' mm';
        document.getElementById('sel-min').textContent = '(' + box.min.x.toFixed(1) + ', ' + box.min.y.toFixed(1) + ', ' + box.min.z.toFixed(1) + ')';
        document.getElementById('sel-max').textContent = '(' + box.max.x.toFixed(1) + ', ' + box.max.y.toFixed(1) + ', ' + box.max.z.toFixed(1) + ')';
        document.getElementById('sel-center').textContent = '(' + center.x.toFixed(1) + ', ' + center.y.toFixed(1) + ', ' + center.z.toFixed(1) + ')';

        updateTransformFields(p);
        populatePartAnchors(selectedPart);
        var partToggle = document.getElementById('sel-anchors-toggle');
        if (!partToggle.checked) {
            selectedPartAnchorsOn = false;
        }
        updateAnchorVisibility();

        if (transformMode) {
            tfc.attach(p.group);
            tfc.visible = true;
            tfc.enabled = true;
        }

        if (hitPoint) {
            var pt = hitPoint.point;
            document.getElementById('sel-pos').textContent = '(' + pt.x.toFixed(1) + ', ' + pt.y.toFixed(1) + ', ' + pt.z.toFixed(1) + ')';
            if (hitPoint.face) {
                var n = hitPoint.face.normal;
                document.getElementById('sel-normal').textContent = '(' + n.x.toFixed(3) + ', ' + n.y.toFixed(3) + ', ' + n.z.toFixed(3) + ')';
            }
            document.getElementById('sel-dist').textContent = pt.length().toFixed(1) + ' mm';
            selMarker.position.copy(pt); selMarker.visible = true;
        } else {
            document.getElementById('sel-pos').textContent = '-';
            document.getElementById('sel-normal').textContent = '-';
            document.getElementById('sel-dist').textContent = '-';
            selMarker.visible = false;
        }
        updatePartsList();
        if (typeof updateDirArrow === 'function') updateDirArrow();
    }

    // Click detection
    var mouseDownPos = null;
    renderer.domElement.addEventListener('mousedown', function(e) { mouseDownPos = { x: e.clientX, y: e.clientY }; });
    renderer.domElement.addEventListener('mouseup', function(e) {
        if (!mouseDownPos) return;
        if (Math.abs(e.clientX - mouseDownPos.x) > 5 || Math.abs(e.clientY - mouseDownPos.y) > 5) return;
        if (tfc.dragging) return;
        mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, cam);
        var meshes = [];
        var names = Object.keys(parts);
        for (var i = 0; i < names.length; i++) if (parts[names[i]].visible) meshes.push(parts[names[i]].mesh);
        var hits = raycaster.intersectObjects(meshes);
        if (hits.length > 0) {
            selectPart(hits[0].object.userData.partName, hits[0]);
        } else {
            selectedPart = null; clearHighlight(); selMarker.visible = false;
            detachTransform();
            document.getElementById('selection-panel').style.display = 'none';
            document.getElementById('sel-anchors-toggle').checked = false;
            selectedPartAnchorsOn = false;
            updateAnchorVisibility();
            updatePartsList();
        }
    });

    var groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    var groundPt = new THREE.Vector3();
    var coordX = document.getElementById('coord-x');
    var coordY = document.getElementById('coord-y');
    var coordZ = document.getElementById('coord-z');

    renderer.domElement.addEventListener('pointermove', function(e) {
        mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, cam);
        var meshes = [];
        var names = Object.keys(parts);
        for (var i = 0; i < names.length; i++) if (parts[names[i]].visible) meshes.push(parts[names[i]].mesh);
        var hits = raycaster.intersectObjects(meshes);
        if (hits.length > 0) {
            var pt = hits[0].point;
            coordX.textContent = pt.x.toFixed(1);
            coordY.textContent = pt.y.toFixed(1);
            coordZ.textContent = pt.z.toFixed(1);
            renderer.domElement.style.cursor = 'pointer';
        } else {
            if (raycaster.ray.intersectPlane(groundPlane, groundPt)) {
                coordX.textContent = groundPt.x.toFixed(1);
                coordY.textContent = '0.0';
                coordZ.textContent = groundPt.z.toFixed(1);
            } else {
                coordX.textContent = '---';
                coordY.textContent = '---';
                coordZ.textContent = '---';
            }
            renderer.domElement.style.cursor = 'default';
        }
    });

    // File input for adding custom STLs
    document.getElementById('file-input').addEventListener('change', function(e) {
        var files = Array.prototype.slice.call(e.target.files);
        files.forEach(function(file) {
            var reader = new FileReader();
            reader.onload = function(ev) {
                try {
                    var geo = loader.parse(ev.target.result);
                    geo.computeVertexNormals();
                    var name = file.name.replace(/\.stl$/i, '');
                    addPart(name, file.name, '#8ecae6', geo, file.size);
                    fitCamera();
                } catch(err) { console.error('Failed:', file.name, err); }
            };
            reader.readAsArrayBuffer(file);
        });
        e.target.value = '';
    });

    // Drag and drop
    var dragCounter = 0;
    var dropZone = document.getElementById('drop-zone');
    document.addEventListener('dragenter', function(e) { e.preventDefault(); dragCounter++; dropZone.style.display = 'flex'; });
    document.addEventListener('dragover', function(e) { e.preventDefault(); });
    document.addEventListener('dragleave', function() { dragCounter--; if (dragCounter <= 0) { dragCounter = 0; dropZone.style.display = 'none'; } });
    document.addEventListener('drop', function(e) {
        e.preventDefault(); dragCounter = 0; dropZone.style.display = 'none';
        var items = e.dataTransfer.files;
        for (var i = 0; i < items.length; i++) {
            if (!items[i].name.toLowerCase().endsWith('.stl')) continue;
            (function(file) {
                var reader = new FileReader();
                reader.onload = function(ev) {
                    try {
                        var geo = loader.parse(ev.target.result);
                        geo.computeVertexNormals();
                        var name = file.name.replace(/\.stl$/i, '');
                        addPart(name, file.name, '#8ecae6', geo, file.size);
                        fitCamera();
                    } catch(err) { console.error('Failed:', file.name, err); }
                };
                reader.readAsArrayBuffer(file);
            })(items[i]);
        }
    });

    // Toolbar
    document.getElementById('color-picker').addEventListener('input', function(e) {
        if (selectedPart && parts[selectedPart]) parts[selectedPart].mesh.material.color.set(e.target.value);
    });
    document.getElementById('btn-wireframe').addEventListener('click', function() {
        wireframeOn = !wireframeOn;
        var names = Object.keys(parts);
        var edgeAngle = 15 * Math.PI / 180;
        for (var i = 0; i < names.length; i++) {
            var p = parts[names[i]];
            if (wireframeOn) {
                p.mesh.material.transparent = true;
                p.mesh.material.opacity = 0.15;
                p.mesh.material.depthWrite = false;
                if (!p.edges) {
                    var edgeGeo = new THREE.EdgesGeometry(p.geometry, edgeAngle);
                    var edgeMat = new THREE.LineBasicMaterial({ color: p.mesh.material.color, linewidth: 1 });
                    p.edges = new THREE.LineSegments(edgeGeo, edgeMat);
                    p.mesh.add(p.edges);
                }
                p.edges.visible = true;
            } else {
                p.mesh.material.transparent = false;
                p.mesh.material.opacity = 1.0;
                p.mesh.material.depthWrite = true;
                if (p.edges) p.edges.visible = false;
            }
            p.mesh.material.needsUpdate = true;
        }
        this.classList.toggle('active', wireframeOn);
    });
    document.getElementById('btn-reset').addEventListener('click', function() {
        cam.position.set(400, 300, 500); controls.target.set(0, 40, 0); controls.update();
    });
    document.getElementById('btn-center').addEventListener('click', fitCamera);
    var axesVis = true;
    document.getElementById('btn-axes').addEventListener('click', function() {
        axesVis = !axesVis; axH.visible = axesVis; axLabels.visible = axesVis;
        this.classList.toggle('active', axesVis);
    });
    var bgColors = { light: 0xf0f0f5, mid: 0xe0e0e8, dark: 0x1a1a2e };
    ['dark', 'mid', 'light'].forEach(function(key) {
        document.getElementById('btn-bg-' + key).addEventListener('click', function() {
            scene.background.setHex(bgColors[key]); scene.fog.color.setHex(bgColors[key]);
        });
    });
    // KiCad export
    document.getElementById('btn-kicad').addEventListener('click', function() {
        var names = Object.keys(KICAD_FILES);
        if (names.length === 0) {
            alert('No KiCad files embedded. Run the gerber exporter to generate them.');
            return;
        }
        for (var i = 0; i < names.length; i++) {
            var fname = names[i];
            var b64 = KICAD_FILES[fname];
            var blob = new Blob([atob(b64)], { type: 'application/octet-stream' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = fname;
            a.click();
            URL.revokeObjectURL(a.href);
        }
    });

    // Delete All
    document.getElementById('btn-delete-all').addEventListener('click', function() {
        var names = Object.keys(parts);
        for (var i = 0; i < names.length; i++) {
            var p = parts[names[i]];
            scene.remove(p.mesh);
            if (p.mesh.geometry) p.mesh.geometry.dispose();
            if (p.mesh.material) p.mesh.material.dispose();
        }
        parts = {};
        selectedPart = null;
        document.getElementById('parts-container').innerHTML = '';
        document.getElementById('selection-panel').style.display = 'none';
        document.getElementById('sel-anchors-toggle').checked = false;
        selectedPartAnchorsOn = false;
        updateAnchorVisibility();
    });

    // ---- Transform manipulation buttons ----
    document.getElementById('btn-move').addEventListener('click', function() { setTransformMode('translate'); });
    document.getElementById('btn-rotate').addEventListener('click', function() { setTransformMode('rotate'); });

    function applySnap() {
        if (snapEnabled) {
            tfc.setTranslationSnap(snapGrid);
            tfc.setRotationSnap(THREE.MathUtils.degToRad(snapAngle));
        } else {
            tfc.setTranslationSnap(null);
            tfc.setRotationSnap(null);
        }
    }

    document.getElementById('btn-snap-settings').addEventListener('click', function() {
        var panel = document.getElementById('snap-panel');
        panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
    });

    document.getElementById('snap-enabled').addEventListener('change', function() {
        snapEnabled = this.checked;
        applySnap();
    });

    document.getElementById('snap-translate').addEventListener('change', function() {
        snapGrid = parseFloat(this.value);
        applySnap();
    });

    document.getElementById('snap-rotate').addEventListener('change', function() {
        snapAngle = parseFloat(this.value);
        applySnap();
    });

    // ---- Directional Move ----
    var dirArrow = null;
    var pickingDirection = false;
    var pickPoint1 = null;

    function getDirVector() {
        var az = parseFloat(document.getElementById('dm-azimuth').value) * Math.PI / 180;
        var el = parseFloat(document.getElementById('dm-elevation').value) * Math.PI / 180;
        return new THREE.Vector3(
            Math.cos(el) * Math.sin(az),
            Math.sin(el),
            Math.cos(el) * Math.cos(az)
        );
    }

    function updateDirDisplay() {
        var v = getDirVector();
        document.getElementById('dm-vec-display').textContent =
            'Direction: (' + v.x.toFixed(2) + ', ' + v.y.toFixed(2) + ', ' + v.z.toFixed(2) + ')';
        updateDirArrow();
    }

    function updateDirArrow() {
        if (dirArrow) { scene.remove(dirArrow); dirArrow = null; }
        if (!selectedPart || !parts[selectedPart]) return;
        var panel = document.getElementById('dir-move-panel');
        if (panel.style.display !== 'block') return;
        var group = parts[selectedPart].group;
        var dir = getDirVector();
        var dist = parseFloat(document.getElementById('dm-distance').value) || 10;
        var len = Math.max(dist, 20);
        var arrowColor = 0xf0a030;
        dirArrow = new THREE.ArrowHelper(dir, group.position.clone(), len, arrowColor, len * 0.15, len * 0.08);
        scene.add(dirArrow);
    }

    function removeDirArrow() {
        if (dirArrow) { scene.remove(dirArrow); dirArrow = null; }
    }

    document.getElementById('btn-dir-move').addEventListener('click', function() {
        var panel = document.getElementById('dir-move-panel');
        if (panel.style.display === 'block') {
            panel.style.display = 'none';
            removeDirArrow();
            pickingDirection = false;
            pickPoint1 = null;
        } else {
            panel.style.display = 'block';
            updateDirDisplay();
        }
    });

    document.getElementById('dm-azimuth').addEventListener('input', updateDirDisplay);
    document.getElementById('dm-elevation').addEventListener('input', updateDirDisplay);
    document.getElementById('dm-distance').addEventListener('input', updateDirArrow);

    document.getElementById('dm-apply').addEventListener('click', function() {
        if (!selectedPart || !parts[selectedPart]) return;
        var p = parts[selectedPart];
        var dir = getDirVector();
        var dist = parseFloat(document.getElementById('dm-distance').value) || 0;
        p.group.position.add(dir.multiplyScalar(dist));
        updateTransformFields(p);
        updateDirArrow();
    });

    // Two-point direction picking
    document.getElementById('dm-pick-dir').addEventListener('click', function() {
        pickingDirection = !pickingDirection;
        pickPoint1 = null;
        this.classList.toggle('active', pickingDirection);
        document.getElementById('dm-pick-status').textContent = pickingDirection
            ? 'Click first point on a surface...'
            : 'Click two points in scene to define direction';
    });

    renderer.domElement.addEventListener('click', function(ev) {
        if (!pickingDirection) return;
        var rect = renderer.domElement.getBoundingClientRect();
        var m = new THREE.Vector2(
            ((ev.clientX - rect.left) / rect.width) * 2 - 1,
            -((ev.clientY - rect.top) / rect.height) * 2 + 1
        );
        var rc = new THREE.Raycaster();
        rc.setFromCamera(m, cam);
        var meshes = [];
        var names = Object.keys(parts);
        for (var i = 0; i < names.length; i++) { meshes.push(parts[names[i]].mesh); }
        var hits = rc.intersectObjects(meshes, false);
        if (hits.length === 0) return;
        var pt = hits[0].point;
        if (!pickPoint1) {
            pickPoint1 = pt.clone();
            document.getElementById('dm-pick-status').textContent =
                'Point 1: (' + pt.x.toFixed(1) + ', ' + pt.y.toFixed(1) + ', ' + pt.z.toFixed(1) + ') — click second point...';
        } else {
            var dir = pt.clone().sub(pickPoint1);
            var len = dir.length();
            if (len < 0.001) { pickPoint1 = null; return; }
            dir.normalize();
            var el = Math.asin(Math.max(-1, Math.min(1, dir.y)));
            var az = Math.atan2(dir.x, dir.z);
            if (az < 0) az += 2 * Math.PI;
            document.getElementById('dm-azimuth').value = (az * 180 / Math.PI).toFixed(1);
            document.getElementById('dm-elevation').value = (el * 180 / Math.PI).toFixed(1);
            document.getElementById('dm-distance').value = len.toFixed(1);
            document.getElementById('dm-pick-status').textContent =
                'Direction set from two points (distance: ' + len.toFixed(1) + ' mm)';
            pickingDirection = false;
            pickPoint1 = null;
            document.getElementById('dm-pick-dir').classList.remove('active');
            updateDirDisplay();
        }
        ev.stopPropagation();
    }, true);

    // Close directional move panel via close button
    document.querySelector('#dir-move-panel .close-btn').addEventListener('click', function() {
        document.getElementById('dir-move-panel').style.display = 'none';
        removeDirArrow();
        pickingDirection = false;
        pickPoint1 = null;
        document.getElementById('dm-pick-dir').classList.remove('active');
    });

    document.getElementById('btn-reset-part').addEventListener('click', function() {
        if (!selectedPart || !parts[selectedPart] || !originalTransforms[selectedPart]) return;
        var p = parts[selectedPart];
        var orig = originalTransforms[selectedPart];
        p.group.position.copy(orig.pos);
        p.group.rotation.copy(orig.rot);
        updateTransformFields(p);
    });

    document.getElementById('btn-export-pos').addEventListener('click', function() {
        var exported = [];
        for (var i = 0; i < partOrder.length; i++) {
            var name = partOrder[i];
            var p = parts[name];
            if (!p) continue;
            var group = p.group;
            var orig = originalTransforms[name];
            if (!orig) continue;
            var dx = group.position.x - orig.pos.x;
            var dy = group.position.y - orig.pos.y;
            var dz = group.position.z - orig.pos.z;
            var dzup_x = dx;
            var dzup_y = -dz;
            var dzup_z = dy;
            var embPart = null;
            for (var j = 0; j < EMBEDDED_PARTS.length; j++) {
                if (EMBEDDED_PARTS[j].name === name) { embPart = EMBEDDED_PARTS[j]; break; }
            }
            var origZup = embPart && embPart.pos_zup ? embPart.pos_zup : [0, 0, 0];
            var origRotZup = embPart && embPart.rot_zup ? embPart.rot_zup : [0, 0, 0];
            var dRx = THREE.MathUtils.radToDeg(group.rotation.x - orig.rot.x);
            var dRy = THREE.MathUtils.radToDeg(group.rotation.y - orig.rot.y);
            var dRz = THREE.MathUtils.radToDeg(group.rotation.z - orig.rot.z);
            var hasDelta = Math.abs(dx) > 0.01 || Math.abs(dy) > 0.01 || Math.abs(dz) > 0.01 ||
                           Math.abs(dRx) > 0.01 || Math.abs(dRy) > 0.01 || Math.abs(dRz) > 0.01;
            exported.push({
                name: name,
                pos_zup: [
                    parseFloat((origZup[0] + dzup_x).toFixed(2)),
                    parseFloat((origZup[1] + dzup_y).toFixed(2)),
                    parseFloat((origZup[2] + dzup_z).toFixed(2))
                ],
                rot_zup: origRotZup,
                modified: hasDelta,
                delta_mm: hasDelta ? [
                    parseFloat(dzup_x.toFixed(2)),
                    parseFloat(dzup_y.toFixed(2)),
                    parseFloat(dzup_z.toFixed(2))
                ] : null,
            });
        }
        var json = JSON.stringify(exported.filter(function(e) { return e.modified; }), null, 2);
        if (json === '[]') {
            alert('No parts have been moved. Select a part and use Move/Rotate to reposition it.');
            return;
        }
        var blob = new Blob([json], { type: 'application/json' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'part_positions.json';
        a.click();
        URL.revokeObjectURL(a.href);
    });

    // Save Configuration (model_configuration.json). Place in project output dir
    // to apply these positions/rotations on next rebuild.
    document.getElementById('btn-save-config').addEventListener('click', function() {
        var config = { parts: [], exported_at: new Date().toISOString() };
        for (var i = 0; i < partOrder.length; i++) {
            var name = partOrder[i];
            var p = parts[name];
            if (!p) continue;
            var group = p.group;
            config.parts.push({
                name: name,
                position: [
                    parseFloat(group.position.x.toFixed(4)),
                    parseFloat(group.position.y.toFixed(4)),
                    parseFloat(group.position.z.toFixed(4))
                ],
                rotation: [
                    parseFloat(THREE.MathUtils.radToDeg(group.rotation.x).toFixed(4)),
                    parseFloat(THREE.MathUtils.radToDeg(group.rotation.y).toFixed(4)),
                    parseFloat(THREE.MathUtils.radToDeg(group.rotation.z).toFixed(4))
                ],
                visible: p.visible
            });
        }
        var json = JSON.stringify(config, null, 2);
        var blob = new Blob([json], { type: 'application/json' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'model_configuration.json';
        a.click();
        URL.revokeObjectURL(a.href);
    });

    // Load Configuration
    var loadConfigInput = document.createElement('input');
    loadConfigInput.type = 'file';
    loadConfigInput.accept = '.json';
    loadConfigInput.style.display = 'none';
    document.body.appendChild(loadConfigInput);

    document.getElementById('btn-load-config').addEventListener('click', function() {
        loadConfigInput.click();
    });

    loadConfigInput.addEventListener('change', function(e) {
        var file = e.target.files[0];
        if (!file) return;
        var reader = new FileReader();
        reader.onload = function(ev) {
            try {
                var config = JSON.parse(ev.target.result);
                if (!config.parts || !Array.isArray(config.parts)) {
                    alert('Invalid configuration file: missing "parts" array.');
                    return;
                }
                var applied = 0;
                for (var i = 0; i < config.parts.length; i++) {
                    var cp = config.parts[i];
                    var p = parts[cp.name];
                    if (!p) continue;
                    var group = p.group;
                    if (cp.position && cp.position.length === 3) {
                        group.position.set(cp.position[0], cp.position[1], cp.position[2]);
                    }
                    if (cp.rotation && cp.rotation.length === 3) {
                        group.rotation.set(
                            THREE.MathUtils.degToRad(cp.rotation[0]),
                            THREE.MathUtils.degToRad(cp.rotation[1]),
                            THREE.MathUtils.degToRad(cp.rotation[2])
                        );
                    }
                    if (typeof cp.visible === 'boolean') {
                        p.visible = cp.visible;
                        group.visible = cp.visible;
                        var eyeEl = document.querySelector('.part-item[data-part="' + cp.name + '"] .eye');
                        if (eyeEl) {
                            if (cp.visible) { eyeEl.classList.add('visible'); }
                            else { eyeEl.classList.remove('visible'); }
                        }
                    }
                    applied++;
                }
                if (selectedPart && parts[selectedPart]) {
                    updateTransformFields(parts[selectedPart]);
                    selectPart(selectedPart, null);
                }
                alert('Configuration loaded: ' + applied + ' part(s) updated.');
            } catch (err) {
                alert('Failed to parse configuration file: ' + err.message);
            }
        };
        reader.readAsText(file);
        loadConfigInput.value = '';
    });

    // Transform input fields
    ['px', 'py', 'pz', 'rx', 'ry', 'rz'].forEach(function(id) {
        document.getElementById('tf-' + id).addEventListener('change', function() {
            if (!selectedPart || !parts[selectedPart]) return;
            var group = parts[selectedPart].group;
            var val = parseFloat(this.value) || 0;
            if (id === 'px') group.position.x = val;
            else if (id === 'py') group.position.y = val;
            else if (id === 'pz') group.position.z = val;
            else if (id === 'rx') group.rotation.x = THREE.MathUtils.degToRad(val);
            else if (id === 'ry') group.rotation.y = THREE.MathUtils.degToRad(val);
            else if (id === 'rz') group.rotation.z = THREE.MathUtils.degToRad(val);
            updateTransformFields(parts[selectedPart]);
        });
    });

    // ---- Dropdown menus ----
    document.querySelectorAll('.dropdown-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var dd = this.parentElement;
            var wasOpen = dd.classList.contains('open');
            document.querySelectorAll('.dropdown.open').forEach(function(d) { d.classList.remove('open'); });
            if (!wasOpen) dd.classList.add('open');
        });
    });
    document.addEventListener('click', function() {
        document.querySelectorAll('.dropdown.open').forEach(function(d) { d.classList.remove('open'); });
    });
    document.querySelectorAll('.dropdown-item').forEach(function(item) {
        item.addEventListener('click', function() {
            this.closest('.dropdown').classList.remove('open');
        });
    });

    // ---- Draggable panels ----
    document.querySelectorAll('.draggable-panel').forEach(function(panel) {
        var handle = panel.querySelector('.drag-handle');
        if (!handle) return;
        var dragging = false, startX, startY, origX, origY;
        handle.addEventListener('mousedown', function(e) {
            if (e.target.classList.contains('close-btn')) return;
            dragging = true;
            var rect = panel.getBoundingClientRect();
            panel.style.left = rect.left + 'px';
            panel.style.top = rect.top + 'px';
            panel.style.right = 'auto';
            panel.style.bottom = 'auto';
            panel.style.transform = 'none';
            startX = e.clientX;
            startY = e.clientY;
            origX = rect.left;
            origY = rect.top;
            e.preventDefault();
        });
        document.addEventListener('mousemove', function(e) {
            if (!dragging) return;
            panel.style.left = Math.max(0, origX + e.clientX - startX) + 'px';
            panel.style.top = Math.max(0, origY + e.clientY - startY) + 'px';
        });
        document.addEventListener('mouseup', function() { dragging = false; });
    });
    // Close buttons
    document.querySelectorAll('.close-btn[data-closes]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var panel = document.getElementById(this.getAttribute('data-closes'));
            if (panel) panel.style.display = 'none';
            document.getElementById('btn-shortcuts').classList.remove('active');
        });
    });

    // Shortcuts panel toggle
    document.getElementById('btn-shortcuts').addEventListener('click', function() {
        var panel = document.getElementById('keymap-panel');
        var vis = panel.style.display === 'block';
        panel.style.display = vis ? 'none' : 'block';
        this.classList.toggle('active', !vis);
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT') return;
        if (e.key === 'g' || e.key === 'G') { setTransformMode('translate'); e.preventDefault(); }
        else if (e.key === 'r' && !e.ctrlKey && !e.metaKey) { setTransformMode('rotate'); e.preventDefault(); }
        else if (e.key === 'Escape') {
            detachTransform();
            document.getElementById('keymap-panel').style.display = 'none';
            document.getElementById('btn-shortcuts').classList.remove('active');
            document.querySelectorAll('.dropdown.open').forEach(function(d) { d.classList.remove('open'); });
            e.preventDefault();
        }
    });

    window.addEventListener('resize', function() {
        cam.aspect = window.innerWidth / window.innerHeight;
        cam.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    // Render loop
    function animate() { requestAnimationFrame(animate); controls.update(); renderer.render(scene, cam); }
    animate();

    // ---- Anchor points and constraint lines ----
    var anchorGroup = new THREE.Group();
    anchorGroup.visible = false;
    scene.add(anchorGroup);
    var anchorSpheres = [];
    var constraintLines = [];
    var anchorsBuilt = false;
    var selectedPartAnchorsOn = false;

    var anchorTooltip = document.createElement('div');
    anchorTooltip.style.cssText = 'position:fixed;z-index:300;background:rgba(16,16,32,0.95);color:#e0e0e0;' +
        'font-size:11px;padding:6px 10px;border-radius:6px;border:1px solid rgba(142,202,230,0.3);' +
        'pointer-events:none;display:none;font-family:SF Mono,Fira Code,monospace;white-space:nowrap;';
    document.body.appendChild(anchorTooltip);

    function getAnchorKind(partName, anchorName) {
        for (var i = 0; i < EMBEDDED_CONSTRAINTS.length; i++) {
            var c = EMBEDDED_CONSTRAINTS[i];
            if ((c.child_part === partName && c.child_anchor === anchorName) ||
                (c.parent_part === partName && c.parent_anchor === anchorName)) {
                return c.kind || 'mate';
            }
        }
        return 'unused';
    }

    function anchorColor(kind) {
        if (kind === 'mate') return 0xff4444;
        if (kind === 'align') return 0x44ff44;
        if (kind === 'offset') return 0x4488ff;
        return 0x888888;
    }

    function constraintLineColor(kind) {
        if (kind === 'mate') return 0xffff00;
        if (kind === 'offset') return 0x00ffff;
        if (kind === 'align') return 0x44ff44;
        return 0xffff00;
    }

    function buildAnchors() {
        if (anchorsBuilt) return;
        anchorsBuilt = true;
        var sphereGeo = new THREE.SphereGeometry(4, 16, 16);

        for (var i = 0; i < EMBEDDED_PARTS.length; i++) {
            var ep = EMBEDDED_PARTS[i];
            var anchors = ep.anchors || [];
            for (var j = 0; j < anchors.length; j++) {
                var a = anchors[j];
                var kind = getAnchorKind(ep.name, a.name);
                var mat = new THREE.MeshBasicMaterial({ color: anchorColor(kind), depthTest: false, transparent: true, opacity: 0.85 });
                var sphere = new THREE.Mesh(sphereGeo, mat);
                sphere.renderOrder = 998;
                var pt = a.point || [0, 0, 0];
                sphere.position.set(pt[0], pt[2], -pt[1]);
                anchorGroup.add(sphere);
                anchorSpheres.push({ mesh: sphere, partName: ep.name, anchorName: a.name, kind: kind });
            }
        }

        for (var ci = 0; ci < EMBEDDED_CONSTRAINTS.length; ci++) {
            var con = EMBEDDED_CONSTRAINTS[ci];
            var p1 = findAnchorPoint(con.child_part, con.child_anchor);
            var p2 = findAnchorPoint(con.parent_part, con.parent_anchor);
            if (p1 && p2) {
                var lineGeo = new THREE.BufferGeometry().setFromPoints([
                    new THREE.Vector3(p1[0], p1[2], -p1[1]),
                    new THREE.Vector3(p2[0], p2[2], -p2[1])
                ]);
                var lineMat = new THREE.LineBasicMaterial({
                    color: constraintLineColor(con.kind),
                    depthTest: false,
                    linewidth: 1
                });
                var line = new THREE.Line(lineGeo, lineMat);
                line.renderOrder = 997;
                anchorGroup.add(line);
                constraintLines.push({ line: line, childPart: con.child_part, parentPart: con.parent_part });
            }
        }
    }

    function findAnchorPoint(partName, anchorName) {
        for (var i = 0; i < EMBEDDED_PARTS.length; i++) {
            if (EMBEDDED_PARTS[i].name !== partName) continue;
            var anchors = EMBEDDED_PARTS[i].anchors || [];
            for (var j = 0; j < anchors.length; j++) {
                if (anchors[j].name === anchorName) return anchors[j].point;
            }
        }
        return null;
    }

    function updateAnchorVisibility() {
        var globalOn = document.getElementById('btn-anchors').checked;
        var partFilter = selectedPartAnchorsOn ? selectedPart : null;
        var anyVisible = globalOn || partFilter;

        if (!anyVisible) {
            anchorGroup.visible = false;
            anchorTooltip.style.display = 'none';
            return;
        }

        buildAnchors();
        anchorGroup.visible = true;

        for (var i = 0; i < anchorSpheres.length; i++) {
            var sphere = anchorSpheres[i];
            sphere.mesh.visible = globalOn || sphere.partName === partFilter;
        }
        for (var j = 0; j < constraintLines.length; j++) {
            var cl = constraintLines[j];
            cl.line.visible = globalOn || cl.childPart === partFilter || cl.parentPart === partFilter;
        }
    }

    function populatePartAnchors(partName) {
        var listEl = document.getElementById('sel-anchor-list');
        var countEl = document.getElementById('sel-anchor-count');
        listEl.innerHTML = '';
        var embPart = null;
        for (var i = 0; i < EMBEDDED_PARTS.length; i++) {
            if (EMBEDDED_PARTS[i].name === partName) { embPart = EMBEDDED_PARTS[i]; break; }
        }
        var anchors = embPart ? (embPart.anchors || []) : [];
        countEl.textContent = anchors.length;
        for (var j = 0; j < anchors.length; j++) {
            var a = anchors[j];
            var kind = getAnchorKind(partName, a.name);
            var row = document.createElement('div');
            row.className = 'anchor-item';
            row.innerHTML = '<span class="anchor-name">' + a.name + '</span>' +
                '<span class="anchor-kind anchor-kind-' + kind + '">' + kind + '</span>';
            listEl.appendChild(row);
        }
    }

    document.getElementById('btn-anchors').addEventListener('change', function() {
        updateAnchorVisibility();
    });

    document.getElementById('sel-anchors-toggle').addEventListener('change', function() {
        selectedPartAnchorsOn = this.checked;
        updateAnchorVisibility();
    });

    // Hover detection for anchor spheres
    var anchorRaycaster = new THREE.Raycaster();
    var anchorMouse = new THREE.Vector2();
    renderer.domElement.addEventListener('pointermove', function(e) {
        if (!anchorGroup.visible || anchorSpheres.length === 0) return;
        anchorMouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        anchorMouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        anchorRaycaster.setFromCamera(anchorMouse, cam);
        var visibleSpheres = [];
        for (var i = 0; i < anchorSpheres.length; i++) {
            if (anchorSpheres[i].mesh.visible) visibleSpheres.push(anchorSpheres[i].mesh);
        }
        var hits = anchorRaycaster.intersectObjects(visibleSpheres);
        if (hits.length > 0) {
            var hitMesh = hits[0].object;
            for (var k = 0; k < anchorSpheres.length; k++) {
                if (anchorSpheres[k].mesh === hitMesh) {
                    var info = anchorSpheres[k];
                    anchorTooltip.textContent = info.partName + ' / ' + info.anchorName + ' (' + info.kind + ')';
                    anchorTooltip.style.display = 'block';
                    anchorTooltip.style.left = (e.clientX + 14) + 'px';
                    anchorTooltip.style.top = (e.clientY - 10) + 'px';
                    break;
                }
            }
        } else {
            anchorTooltip.style.display = 'none';
        }
    });

    // ---- Panel drag / collapse / resize ----
    (function() {
        function makeDraggable(panel, handle) {
            var dragging = false, startX, startY, startLeft, startTop;
            handle.style.cursor = 'grab';
            handle.addEventListener('mousedown', function(e) {
                if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;
                dragging = true;
                handle.style.cursor = 'grabbing';
                panel.classList.add('panel-dragging');
                var rect = panel.getBoundingClientRect();
                startX = e.clientX;
                startY = e.clientY;
                startLeft = rect.left;
                startTop = rect.top;
                panel.style.right = 'auto';
                panel.style.bottom = 'auto';
                panel.style.left = startLeft + 'px';
                panel.style.top = startTop + 'px';
                e.preventDefault();
            });
            window.addEventListener('mousemove', function(e) {
                if (!dragging) return;
                var dx = e.clientX - startX;
                var dy = e.clientY - startY;
                panel.style.left = Math.max(0, startLeft + dx) + 'px';
                panel.style.top = Math.max(0, startTop + dy) + 'px';
            });
            window.addEventListener('mouseup', function() {
                if (dragging) {
                    dragging = false;
                    handle.style.cursor = 'grab';
                    panel.classList.remove('panel-dragging');
                }
            });
        }

        var sidebar = document.getElementById('parts-list');
        var toggle = document.getElementById('sidebar-toggle');
        var sidebarHeader = sidebar.querySelector('.sidebar-header');
        var resizeHandle = document.getElementById('sidebar-resize-handle');
        var sidebarCollapsed = false;
        var sidebarWidth = 220;

        makeDraggable(sidebar, sidebarHeader);

        toggle.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebarCollapsed = !sidebarCollapsed;
            if (sidebarCollapsed) {
                sidebar.classList.add('collapsed');
                toggle.innerHTML = '&raquo;';
                toggle.title = 'Expand sidebar';
            } else {
                sidebar.classList.remove('collapsed');
                sidebar.style.width = sidebarWidth + 'px';
                toggle.innerHTML = '&laquo;';
                toggle.title = 'Collapse sidebar';
            }
        });

        var resizing = false;
        resizeHandle.addEventListener('mousedown', function(e) {
            if (sidebarCollapsed) return;
            resizing = true;
            sidebar.classList.add('resizing');
            resizeHandle.classList.add('active');
            e.preventDefault();
            e.stopPropagation();
        });
        window.addEventListener('mousemove', function(e) {
            if (!resizing) return;
            var rect = sidebar.getBoundingClientRect();
            var w = Math.max(120, Math.min(e.clientX - rect.left, window.innerWidth * 0.5));
            sidebar.style.width = w + 'px';
            sidebarWidth = w;
        });
        window.addEventListener('mouseup', function() {
            if (resizing) {
                resizing = false;
                sidebar.classList.remove('resizing');
                resizeHandle.classList.remove('active');
            }
        });

        var selPanel = document.getElementById('selection-panel');
        if (selPanel) {
            var selHeader = selPanel.querySelector('h3');
            if (selHeader) {
                makeDraggable(selPanel, selHeader);
            }
        }
    })();

    // ---- Auto-load embedded parts ----
    var loadingMsg = document.getElementById('loading-msg');
    var loadingEl = document.getElementById('loading');
    var total = EMBEDDED_PARTS.length;
    var loaded = 0;

    function loadEmbeddedPart(idx) {
        if (idx >= total) {
            loadingEl.style.display = 'none';
            fitCamera();
            console.log('[VIEWER] All ' + total + ' parts loaded');
            return;
        }
        var p = EMBEDDED_PARTS[idx];
        loadingMsg.textContent = 'Loading ' + (idx + 1) + '/' + total + ': ' + p.display;
        try {
            var binary = atob(p.stl);
            var bytes = new Uint8Array(binary.length);
            for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            var geo = loader.parse(bytes.buffer);
            geo.computeVertexNormals();
            addPart(p.name, p.display, p.color, geo, p.size, p.meta);
            loaded++;
        } catch (e) {
            console.error('[VIEWER] Failed to load embedded part:', p.name, e);
        }
        setTimeout(function() { loadEmbeddedPart(idx + 1); }, 0);
    }

    loadEmbeddedPart(0);
})();
