import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';

var EMBEDDED_PARTS = window.__VIEWER_PARTS;
var KICAD_FILES = window.__VIEWER_KICAD;
var EMBEDDED_CONSTRAINTS = window.__VIEWER_CONSTRAINTS;
var EMBEDDED_BUILD_RESULT = window.__VIEWER_BUILD_RESULT || {};
var OVERLAY_SAVE_HINT = (typeof window.__OVERLAY_SAVE_HINT === 'string') ? window.__OVERLAY_SAVE_HINT : '';

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
    var overlayAnchors = {};
    var overlayConstraints = [];
    var overlayModifications = {};
    var overlayNewParts = [];
    var addAnchorMode = false;
    var modificationIdCounter = 0;
    var newPartIdCounter = 0;
    var placeCutMode = null;
    var placeCutFaceData = null;
    var placeCutPreviewMesh = null;

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

    function addPrimitivePart(type, params) {
        newPartIdCounter++;
        var name = '_new_part_' + newPartIdCounter;
        var geometry;
        var geometryData;
        if (type === 'box') {
            var size = params.size || [20, 20, 10];
            geometry = new THREE.BoxGeometry(size[0], size[1], size[2]);
            geometryData = { type: 'box', size: size };
        } else {
            var r = params.r != null ? params.r : 5;
            var h = params.h != null ? params.h : 10;
            geometry = new THREE.CylinderGeometry(r, r, h, 32);
            geometryData = { type: 'cylinder', r: r, h: h };
        }
        geometry.computeBoundingBox();
        var center = new THREE.Vector3();
        geometry.boundingBox.getCenter(center);
        var color = new THREE.Color(0x8ecae6).convertSRGBToLinear();
        var mat = new THREE.MeshPhysicalMaterial({
            color: color, metalness: 0.2, roughness: 0.4, clearcoat: 0.3, clearcoatRoughness: 0.2,
            side: THREE.DoubleSide
        });
        var mesh = new THREE.Mesh(geometry, mat);
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.userData.partName = name;
        mesh.position.set(-center.x, -center.y, -center.z);
        var group = new THREE.Group();
        group.position.set(0, 0, 0);
        group.add(mesh);
        scene.add(group);
        var display = type === 'box' ? 'New box' : 'New cylinder';
        parts[name] = { group: group, mesh: mesh, geometry: geometry, fileSize: 0, color: '#8ecae6', display: display, visible: true, meta: {}, isNewPart: true, geometryData: geometryData };
        originalTransforms[name] = { pos: group.position.clone(), rot: group.rotation.clone() };
        partOrder.push(name);
        updatePartsList();
        selectPart(name, null);
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

    function revealAllParts() {
        for (var i = 0; i < partOrder.length; i++) {
            var name = partOrder[i];
            var p = parts[name];
            if (p && !p.visible) {
                p.visible = true;
                p.group.visible = true;
            }
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

    function partHasOverlay(name) {
        var hasPos = false;
        var orig = originalTransforms[name];
        if (orig && parts[name]) {
            var g = parts[name].group;
            if (Math.abs(g.position.x - orig.pos.x) > 0.01 || Math.abs(g.position.y - orig.pos.y) > 0.01 || Math.abs(g.position.z - orig.pos.z) > 0.01)
                hasPos = true;
        }
        var hasAnchors = overlayAnchors[name] && overlayAnchors[name].length > 0;
        var hasMods = overlayModifications[name] && overlayModifications[name].length > 0;
        return hasPos || hasAnchors || hasMods;
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
            var overlayBadge = partHasOverlay(name) ? '<span class="overlay-badge" title="Has overlay edits">*</span>' : '';
            div.innerHTML = '<span class="eye ' + (p.visible ? 'visible' : '') + '" data-part="' + name + '">&#9679;</span>' +
                '<span style="flex:1">' + p.display + '</span>' + overlayBadge + '<span class="size">' + sizeKB + '</span>';
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
        populateModificationList(selectedPart);
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
        var saveNewSection = document.getElementById('sel-save-new-part-section');
        if (p.isNewPart) {
            saveNewSection.style.display = 'block';
            document.getElementById('new-part-name').value = '';
            document.getElementById('new-part-display').value = p.display || '';
        } else {
            saveNewSection.style.display = 'none';
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
        if (addWpMode) return; // route waypoint placement handled separately
        mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        raycaster.setFromCamera(mouse, cam);
        var meshes = [];
        var names = Object.keys(parts);
        for (var i = 0; i < names.length; i++) if (parts[names[i]].visible) meshes.push(parts[names[i]].mesh);
        var hits = raycaster.intersectObjects(meshes);
        if (hits.length > 0) {
            if (addAnchorMode) {
                var hit = hits[0];
                var partName = hit.object.userData.partName;
                var group = parts[partName] && parts[partName].group;
                if (group) {
                    var localPoint = hit.point.clone().applyMatrix4(group.matrixWorld.clone().invert());
                    var worldNorm = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
                    var localNorm = worldNorm.transformDirection(group.matrixWorld.clone().invert());
                    var name = prompt('Anchor name (e.g. custom_mount):', 'custom_mount');
                    if (name && name.trim()) {
                        name = name.trim();
                        if (!overlayAnchors[partName]) overlayAnchors[partName] = [];
                        overlayAnchors[partName].push({
                            name: name,
                            point: [localPoint.x, localPoint.y, localPoint.z],
                            normal: [localNorm.x, localNorm.y, localNorm.z]
                        });
                        for (var mi = 0; mi < overlayAnchorMeshes.length; mi++) {
                            if (overlayAnchorMeshes[mi].parent)
                                overlayAnchorMeshes[mi].parent.remove(overlayAnchorMeshes[mi]);
                        }
                        overlayAnchorMeshes = [];
                        for (var si = anchorSpheres.length - 1; si >= 0; si--) {
                            if (anchorSpheres[si].kind === 'viewer') anchorSpheres.splice(si, 1);
                        }
                        var sphereGeo = new THREE.SphereGeometry(4, 16, 16);
                        for (var pn in overlayAnchors) {
                            var p = parts[pn];
                            if (!p || !p.group) continue;
                            var list = overlayAnchors[pn];
                            for (var k = 0; k < list.length; k++) {
                                var a = list[k];
                                var pt = a.point || [0, 0, 0];
                                var mat = new THREE.MeshBasicMaterial({ color: 0xff8800, depthTest: false, transparent: true, opacity: 0.9 });
                                var sphere = new THREE.Mesh(sphereGeo.clone(), mat);
                                sphere.renderOrder = 998;
                                sphere.position.set(pt[0], pt[1], pt[2]);
                                p.group.add(sphere);
                                overlayAnchorMeshes.push(sphere);
                                anchorSpheres.push({ mesh: sphere, partName: pn, anchorName: a.name, kind: 'viewer' });
                            }
                        }
                        updateAnchorVisibility();
                        if (selectedPart === partName) populatePartAnchors(partName);
                        updatePartsList();
                    }
                }
                addAnchorMode = false;
                document.getElementById('btn-add-anchor').classList.remove('active');
                return;
            }
            if (placeCutMode && hits.length > 0) {
                if (hits[0].object.userData.partName !== selectedPart) {
                    cancelPlaceCut();
                }
            }
            if (placeCutMode && hits.length > 0 && hits[0].object.userData.partName === selectedPart) {
                var hit = hits[0];
                var group = parts[selectedPart].group;
                var localPoint = hit.point.clone().applyMatrix4(group.matrixWorld.clone().invert());
                var worldNorm = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
                var localNorm = worldNorm.transformDirection(group.matrixWorld.clone().invert());
                placeCutFaceData = {
                    point: [localPoint.x, localPoint.y, localPoint.z],
                    normal: [localNorm.x, localNorm.y, localNorm.z]
                };
                document.getElementById('sel-place-hint').style.display = 'none';
                var panel = document.getElementById('sel-place-cut-panel');
                var boxFields = document.getElementById('sel-place-cut-box-fields');
                var cylFields = document.getElementById('sel-place-cut-cyl-fields');
                if (placeCutMode === 'cut_box' || placeCutMode === 'add_box') {
                    boxFields.style.display = 'block';
                    cylFields.style.display = 'none';
                } else {
                    boxFields.style.display = 'none';
                    cylFields.style.display = 'block';
                }
                panel.style.display = 'block';
                updatePlaceCutPreview();
                return;
            }
            selectPart(hits[0].object.userData.partName, hits[0]);
        } else {
            if (placeCutMode) cancelPlaceCut();
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
        if (placeCutMode && selectedPart && !placeCutFaceData && parts[selectedPart]) {
            var partMesh = parts[selectedPart].mesh;
            raycaster.setFromCamera(mouse, cam);
            var cutHits = raycaster.intersectObject(partMesh);
            if (cutHits.length > 0) {
                var hit = cutHits[0];
                var group = parts[selectedPart].group;
                var localPoint = hit.point.clone().applyMatrix4(group.matrixWorld.clone().invert());
                var worldNorm = hit.face.normal.clone().transformDirection(hit.object.matrixWorld);
                var localNorm = worldNorm.transformDirection(group.matrixWorld.clone().invert());
                updatePlaceCutPreview([localPoint.x, localPoint.y, localPoint.z], [localNorm.x, localNorm.y, localNorm.z]);
            } else {
                updatePlaceCutPreview(null, null);
            }
        }
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
    document.getElementById('btn-reveal-all').addEventListener('click', revealAllParts);
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

    // Save overlay (viewer_overlay.json). Place in project output dir to apply on next rebuild.
    document.getElementById('btn-save-config').addEventListener('click', function() {
        var partsDict = {};
        for (var i = 0; i < partOrder.length; i++) {
            var name = partOrder[i];
            var p = parts[name];
            if (!p) continue;
            var group = p.group;
            partsDict[name] = {
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
            };
        }
        var newPartsExport = [];
        for (var ni = 0; ni < overlayNewParts.length; ni++) {
            var np = overlayNewParts[ni];
            var p = parts[np.name];
            if (!p || !p.group) continue;
            var g = p.group;
            var geo = p.geometryData || {};
            var geomOut = { type: geo.type || 'box', pos: [g.position.x, g.position.y, g.position.z], rot: [THREE.MathUtils.radToDeg(g.rotation.x), THREE.MathUtils.radToDeg(g.rotation.y), THREE.MathUtils.radToDeg(g.rotation.z)] };
            if (geo.size) geomOut.size = geo.size;
            if (geo.r != null) geomOut.r = geo.r;
            if (geo.h != null) geomOut.h = geo.h;
            newPartsExport.push({ name: np.name, display: np.display, geometry: geomOut });
        }
        var overlay = {
            parts: partsDict,
            anchors: overlayAnchors,
            constraints: overlayConstraints,
            modifications: overlayModifications,
            new_parts: newPartsExport,
            exported_at: new Date().toISOString()
        };
        var json = JSON.stringify(overlay, null, 2);
        var blob = new Blob([json], { type: 'application/json' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'viewer_overlay.json';
        a.click();
        URL.revokeObjectURL(a.href);
        if (OVERLAY_SAVE_HINT) {
            setTimeout(function() { alert(OVERLAY_SAVE_HINT); }, 100);
        }
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

    document.getElementById('btn-add-anchor').addEventListener('click', function() {
        addAnchorMode = true;
        this.classList.add('active');
        document.querySelectorAll('.dropdown.open').forEach(function(d) { d.classList.remove('open'); });
    });

    function getPartAnchors(partName) {
        var out = [];
        for (var i = 0; i < EMBEDDED_PARTS.length; i++) {
            if (EMBEDDED_PARTS[i].name !== partName) continue;
            var anchors = EMBEDDED_PARTS[i].anchors || [];
            for (var j = 0; j < anchors.length; j++) out.push(anchors[j].name);
            break;
        }
        var list = overlayAnchors[partName];
        if (Array.isArray(list)) for (var k = 0; k < list.length; k++) out.push(list[k].name);
        return out;
    }

    (function() {
        var cpSelect = document.getElementById('constraint-child-part');
        var caSelect = document.getElementById('constraint-child-anchor');
        var ppSelect = document.getElementById('constraint-parent-part');
        var paSelect = document.getElementById('constraint-parent-anchor');
        function fillChildAnchors() {
            caSelect.innerHTML = '<option value="">Anchor</option>';
            var part = cpSelect.value;
            if (!part) return;
            var anchors = getPartAnchors(part);
            for (var a = 0; a < anchors.length; a++)
                caSelect.innerHTML += '<option value="' + anchors[a] + '">' + anchors[a] + '</option>';
        }
        function fillParentAnchors() {
            paSelect.innerHTML = '<option value="">Anchor</option>';
            var part = ppSelect.value;
            if (!part) return;
            var anchors = getPartAnchors(part);
            for (var a = 0; a < anchors.length; a++)
                paSelect.innerHTML += '<option value="' + anchors[a] + '">' + anchors[a] + '</option>';
        }
        cpSelect.addEventListener('change', fillChildAnchors);
        ppSelect.addEventListener('change', fillParentAnchors);
        document.getElementById('btn-add-constraint').addEventListener('click', function() {
            document.querySelectorAll('.dropdown.open').forEach(function(d) { d.classList.remove('open'); });
            var panel = document.getElementById('add-constraint-panel');
            cpSelect.innerHTML = '<option value="">Part</option>';
            ppSelect.innerHTML = '<option value="">Part</option>';
            for (var i = 0; i < partOrder.length; i++) {
                var n = partOrder[i];
                cpSelect.innerHTML += '<option value="' + n + '">' + (parts[n].display || n) + '</option>';
                ppSelect.innerHTML += '<option value="' + n + '">' + (parts[n].display || n) + '</option>';
            }
            caSelect.innerHTML = '<option value="">Anchor</option>';
            paSelect.innerHTML = '<option value="">Anchor</option>';
            panel.style.display = 'block';
        });
    })();

    document.getElementById('constraint-add-btn').addEventListener('click', function() {
        var childPart = document.getElementById('constraint-child-part').value;
        var childAnchor = document.getElementById('constraint-child-anchor').value;
        var parentPart = document.getElementById('constraint-parent-part').value;
        var parentAnchor = document.getElementById('constraint-parent-anchor').value;
        var kind = document.getElementById('constraint-kind').value;
        var gap = parseFloat(document.getElementById('constraint-gap').value) || 0;
        if (!childPart || !childAnchor || !parentPart || !parentAnchor) {
            alert('Select child and parent part and anchor.');
            return;
        }
        overlayConstraints.push({
            child_part: childPart, child_anchor: childAnchor,
            parent_part: parentPart, parent_anchor: parentAnchor,
            kind: kind, gap: gap
        });
        var p1 = findAnchorPoint(childPart, childAnchor);
        var p2 = findAnchorPoint(parentPart, parentAnchor);
        if (p1 && p2) {
            var lineGeo = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(p1[0], p1[2], -p1[1]),
                new THREE.Vector3(p2[0], p2[2], -p2[1])
            ]);
            var lineMat = new THREE.LineBasicMaterial({ color: 0xff8800, depthTest: false, linewidth: 1 });
            var line = new THREE.Line(lineGeo, lineMat);
            line.renderOrder = 997;
            anchorGroup.add(line);
            constraintLines.push({ line: line, childPart: childPart, parentPart: parentPart });
        }
        document.getElementById('add-constraint-panel').style.display = 'none';
        updatePartsList();
    });

    loadConfigInput.addEventListener('change', function(e) {
        var file = e.target.files[0];
        if (!file) return;
        var reader = new FileReader();
        reader.onload = function(ev) {
            try {
                var config = JSON.parse(ev.target.result);
                var partsList = config.parts;
                if (Array.isArray(partsList)) {
                    for (var i = 0; i < partsList.length; i++) {
                        var cp = partsList[i];
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
                    }
                } else if (partsList && typeof partsList === 'object') {
                    for (var name in partsList) {
                        var cp = partsList[name];
                        var p = parts[name];
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
                            var eyeEl = document.querySelector('.part-item[data-part="' + name + '"] .eye');
                            if (eyeEl) {
                                if (cp.visible) { eyeEl.classList.add('visible'); }
                                else { eyeEl.classList.remove('visible'); }
                            }
                        }
                    }
                }
                if (config.anchors && typeof config.anchors === 'object') {
                    overlayAnchors = config.anchors;
                }
                if (config.constraints && Array.isArray(config.constraints)) {
                    overlayConstraints = config.constraints;
                }
                if (config.modifications && typeof config.modifications === 'object') {
                    overlayModifications = config.modifications;
                }
                if (config.new_parts && Array.isArray(config.new_parts)) {
                    overlayNewParts = config.new_parts;
                }
                for (var mi = 0; mi < overlayAnchorMeshes.length; mi++) {
                    if (overlayAnchorMeshes[mi].parent)
                        overlayAnchorMeshes[mi].parent.remove(overlayAnchorMeshes[mi]);
                }
                overlayAnchorMeshes = [];
                anchorsBuilt = false;
                if (anchorGroup) {
                    while (anchorGroup.children.length) anchorGroup.children.pop();
                }
                anchorSpheres = [];
                constraintLines = [];
                buildAnchors();
                updateAnchorVisibility();
                if (selectedPart) {
                    populatePartAnchors(selectedPart);
                    updateTransformFields(parts[selectedPart]);
                    selectPart(selectedPart, null);
                }
                updatePartsList();
                alert('Overlay loaded.');
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
            if (this.classList.contains('dropdown-group-label')) return;
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
            // Cancel route waypoint placement mode
            if (addWpMode) {
                addWpMode = false;
                var _addWpBtn = document.getElementById('btn-route-add-wp');
                if (_addWpBtn) _addWpBtn.classList.remove('active');
            }
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
    var overlayAnchorMeshes = [];
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
        if (kind === 'viewer') return 0xff8800;
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
        for (var partName in overlayAnchors) {
            var p = parts[partName];
            if (!p || !p.group) continue;
            var list = overlayAnchors[partName];
            if (!Array.isArray(list)) continue;
            for (var k = 0; k < list.length; k++) {
                var a = list[k];
                var pt = a.point || [0, 0, 0];
                var mat = new THREE.MeshBasicMaterial({ color: 0xff8800, depthTest: false, transparent: true, opacity: 0.9 });
                var sphere = new THREE.Mesh(sphereGeo.clone(), mat);
                sphere.renderOrder = 998;
                sphere.position.set(pt[0], pt[1], pt[2]);
                p.group.add(sphere);
                overlayAnchorMeshes.push(sphere);
                anchorSpheres.push({ mesh: sphere, partName: partName, anchorName: a.name, kind: 'viewer' });
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
        for (var oi = 0; oi < overlayConstraints.length; oi++) {
            var con = overlayConstraints[oi];
            var p1 = findAnchorPoint(con.child_part, con.child_anchor);
            var p2 = findAnchorPoint(con.parent_part, con.parent_anchor);
            if (p1 && p2) {
                var lineGeo = new THREE.BufferGeometry().setFromPoints([
                    new THREE.Vector3(p1[0], p1[2], -p1[1]),
                    new THREE.Vector3(p2[0], p2[2], -p2[1])
                ]);
                var lineMat = new THREE.LineBasicMaterial({
                    color: 0xff8800,
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
        var list = overlayAnchors[partName];
        if (Array.isArray(list)) {
            for (var k = 0; k < list.length; k++) {
                if (list[k].name === anchorName) {
                    var p = parts[partName];
                    if (!p || !p.group) return null;
                    var local = new THREE.Vector3(list[k].point[0], list[k].point[1], list[k].point[2]);
                    var world = local.clone().applyMatrix4(p.group.matrixWorld);
                    return [world.x, world.z, -world.y];
                }
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
        var anchors = embPart ? (embPart.anchors || []).slice() : [];
        var overlayList = overlayAnchors[partName];
        if (Array.isArray(overlayList)) {
            for (var k = 0; k < overlayList.length; k++) {
                anchors.push({ name: overlayList[k].name, kind: 'viewer' });
            }
        }
        countEl.textContent = anchors.length;
        for (var j = 0; j < anchors.length; j++) {
            var a = anchors[j];
            var kind = a.kind || getAnchorKind(partName, a.name);
            var row = document.createElement('div');
            row.className = 'anchor-item';
            row.innerHTML = '<span class="anchor-name">' + a.name + '</span>' +
                '<span class="anchor-kind anchor-kind-' + kind + '">' + kind + '</span>';
            listEl.appendChild(row);
        }
    }

    function populateModificationList(partName) {
        var listEl = document.getElementById('sel-modification-list');
        listEl.innerHTML = '';
        var list = overlayModifications[partName];
        if (!Array.isArray(list) || list.length === 0) {
            listEl.innerHTML = '<span class="sel-value" style="font-size:11px;color:#888;">None</span>';
            return;
        }
        for (var i = 0; i < list.length; i++) {
            var op = list[i];
            var row = document.createElement('div');
            row.className = 'anchor-item';
            row.style.display = 'flex';
            row.style.justifyContent = 'space-between';
            row.style.alignItems = 'center';
            row.innerHTML = '<span>' + (op.type || 'op') + ' ' + (op.id || '') + '</span>' +
                '<button type="button" class="close-btn" style="font-size:10px;padding:2px 6px;" data-remove-mod="' + (op.id || '') + '">Remove</button>';
            listEl.appendChild(row);
        }
        listEl.querySelectorAll('[data-remove-mod]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var id = this.getAttribute('data-remove-mod');
                var list = overlayModifications[partName];
                if (!Array.isArray(list)) return;
                for (var j = list.length - 1; j >= 0; j--) {
                    if (list[j].id === id) { list.splice(j, 1); break; }
                }
                populateModificationList(partName);
                updatePartsList();
            });
        });
    }

    function eulerDegFromNormal(nx, ny, nz) {
        var n = new THREE.Vector3(nx, ny, nz).normalize();
        var zUp = new THREE.Vector3(0, 0, 1);
        var quat = new THREE.Quaternion().setFromUnitVectors(zUp, n);
        var euler = new THREE.Euler().setFromQuaternion(quat);
        return [euler.x * 180 / Math.PI, euler.y * 180 / Math.PI, euler.z * 180 / Math.PI];
    }

    function removePlaceCutPreview() {
        if (placeCutPreviewMesh && placeCutPreviewMesh.parent) {
            placeCutPreviewMesh.parent.remove(placeCutPreviewMesh);
            if (placeCutPreviewMesh.geometry) placeCutPreviewMesh.geometry.dispose();
            if (placeCutPreviewMesh.material) placeCutPreviewMesh.material.dispose();
            placeCutPreviewMesh = null;
        }
    }

    function updatePlaceCutPreview(hoverPointLocal, hoverNormalLocal) {
        if (!placeCutMode || !selectedPart || !parts[selectedPart]) {
            removePlaceCutPreview();
            return;
        }
        var partGroup = parts[selectedPart].group;
        var pt = hoverPointLocal || (placeCutFaceData ? placeCutFaceData.point : null);
        var norm = hoverNormalLocal || (placeCutFaceData ? placeCutFaceData.normal : null);
        if (!pt || !norm) {
            removePlaceCutPreview();
            return;
        }
        var w = 10, d = 10, ext = 10, r = 5, h = 10;
        if (placeCutFaceData) {
            w = parseFloat(document.getElementById('place-width').value) || 10;
            d = parseFloat(document.getElementById('place-depth').value) || 10;
            ext = parseFloat(document.getElementById('place-extent').value) || 10;
            r = parseFloat(document.getElementById('place-radius').value) || 5;
            h = parseFloat(document.getElementById('place-cyl-depth').value) || 10;
        }
        var isBox = placeCutMode === 'cut_box' || placeCutMode === 'add_box';
        var geometry = isBox
            ? new THREE.BoxGeometry(w, d, ext)
            : new THREE.CylinderGeometry(r, r, h, 32);
        var isCut = placeCutMode.indexOf('cut') >= 0;
        var previewColor = isCut ? 0xcc4444 : 0x44aa44;
        var mat = new THREE.MeshPhongMaterial({
            color: previewColor,
            transparent: true,
            opacity: 0.4,
            depthWrite: false,
            side: THREE.DoubleSide
        });
        if (placeCutPreviewMesh) {
            partGroup.remove(placeCutPreviewMesh);
            placeCutPreviewMesh.geometry.dispose();
            placeCutPreviewMesh.material.dispose();
        }
        placeCutPreviewMesh = new THREE.Mesh(geometry, mat);
        placeCutPreviewMesh.position.set(pt[0], pt[1], pt[2]);
        var rotDeg = eulerDegFromNormal(norm[0], norm[1], norm[2]);
        placeCutPreviewMesh.rotation.set(
            THREE.MathUtils.degToRad(rotDeg[0]),
            THREE.MathUtils.degToRad(rotDeg[1]),
            THREE.MathUtils.degToRad(rotDeg[2])
        );
        placeCutPreviewMesh.renderOrder = 1;
        partGroup.add(placeCutPreviewMesh);
    }

    function startPlaceCut(mode) {
        if (!selectedPart) return;
        placeCutMode = mode;
        placeCutFaceData = null;
        removePlaceCutPreview();
        document.getElementById('sel-place-cut-panel').style.display = 'none';
        var hint = document.getElementById('sel-place-hint');
        hint.textContent = 'Click on the part face where you want the ' + (mode.indexOf('cut') >= 0 ? 'cut' : 'add') + '.';
        hint.style.display = 'block';
    }

    function cancelPlaceCut() {
        placeCutMode = null;
        placeCutFaceData = null;
        removePlaceCutPreview();
        document.getElementById('sel-place-hint').style.display = 'none';
        document.getElementById('sel-place-cut-panel').style.display = 'none';
    }

    document.getElementById('btn-add-cut-box').addEventListener('click', function() { startPlaceCut('cut_box'); });
    document.getElementById('btn-add-add-box').addEventListener('click', function() { startPlaceCut('add_box'); });
    document.getElementById('btn-add-cut-cylinder').addEventListener('click', function() { startPlaceCut('cut_cylinder'); });
    document.getElementById('btn-add-add-cylinder').addEventListener('click', function() { startPlaceCut('add_cylinder'); });

    document.getElementById('place-width').addEventListener('input', function() { document.getElementById('place-width-val').textContent = this.value; updatePlaceCutPreview(); });
    document.getElementById('place-depth').addEventListener('input', function() { document.getElementById('place-depth-val').textContent = this.value; updatePlaceCutPreview(); });
    document.getElementById('place-extent').addEventListener('input', function() { document.getElementById('place-extent-val').textContent = this.value; updatePlaceCutPreview(); });
    document.getElementById('place-radius').addEventListener('input', function() { document.getElementById('place-radius-val').textContent = this.value; updatePlaceCutPreview(); });
    document.getElementById('place-cyl-depth').addEventListener('input', function() { document.getElementById('place-cyl-depth-val').textContent = this.value; updatePlaceCutPreview(); });

    document.getElementById('place-apply-btn').addEventListener('click', function() {
        if (!selectedPart || !placeCutFaceData) return;
        removePlaceCutPreview();
        var pt = placeCutFaceData.point;
        var norm = placeCutFaceData.normal;
        var rot_deg = eulerDegFromNormal(norm[0], norm[1], norm[2]);
        modificationIdCounter++;
        if (!overlayModifications[selectedPart]) overlayModifications[selectedPart] = [];
        if (placeCutMode === 'cut_box' || placeCutMode === 'add_box') {
            var w = parseFloat(document.getElementById('place-width').value) || 10;
            var d = parseFloat(document.getElementById('place-depth').value) || 10;
            var ext = parseFloat(document.getElementById('place-extent').value) || 10;
            overlayModifications[selectedPart].push({
                id: 'op_' + modificationIdCounter,
                type: placeCutMode,
                pos: pt,
                size: [w, d, ext],
                rot_deg: rot_deg
            });
        } else {
            var r = parseFloat(document.getElementById('place-radius').value) || 5;
            var h = parseFloat(document.getElementById('place-cyl-depth').value) || 10;
            overlayModifications[selectedPart].push({
                id: 'op_' + modificationIdCounter,
                type: placeCutMode,
                pos: pt,
                r: r,
                h: h,
                rot_deg: rot_deg
            });
        }
        cancelPlaceCut();
        populateModificationList(selectedPart);
        updatePartsList();
    });

    document.getElementById('place-cancel-btn').addEventListener('click', cancelPlaceCut);

    document.getElementById('fillet-radius').addEventListener('input', function() {
        document.getElementById('fillet-radius-val').textContent = this.value;
    });
    document.getElementById('chamfer-dist').addEventListener('input', function() {
        document.getElementById('chamfer-dist-val').textContent = this.value;
    });

    document.getElementById('btn-apply-fillet').addEventListener('click', function() {
        if (!selectedPart) return;
        var val = parseFloat(document.getElementById('fillet-radius').value) || 2;
        if (val <= 0) return;
        modificationIdCounter++;
        if (!overlayModifications[selectedPart]) overlayModifications[selectedPart] = [];
        overlayModifications[selectedPart].push({ id: 'op_' + modificationIdCounter, type: 'fillet', r: val });
        populateModificationList(selectedPart);
        updatePartsList();
    });

    document.getElementById('btn-apply-chamfer').addEventListener('click', function() {
        if (!selectedPart) return;
        var val = parseFloat(document.getElementById('chamfer-dist').value) || 1;
        if (val <= 0) return;
        modificationIdCounter++;
        if (!overlayModifications[selectedPart]) overlayModifications[selectedPart] = [];
        overlayModifications[selectedPart].push({ id: 'op_' + modificationIdCounter, type: 'chamfer', d: val });
        populateModificationList(selectedPart);
        updatePartsList();
    });

    document.getElementById('btn-new-box').addEventListener('click', function() {
        document.querySelectorAll('.dropdown.open').forEach(function(d) { d.classList.remove('open'); });
        addPrimitivePart('box', { size: [20, 20, 10] });
    });
    document.getElementById('btn-new-cylinder').addEventListener('click', function() {
        document.querySelectorAll('.dropdown.open').forEach(function(d) { d.classList.remove('open'); });
        addPrimitivePart('cylinder', { r: 5, h: 10 });
    });

    document.getElementById('btn-save-new-part').addEventListener('click', function() {
        if (!selectedPart || !parts[selectedPart] || !parts[selectedPart].isNewPart) return;
        var partName = (document.getElementById('new-part-name').value || '').trim();
        var displayName = (document.getElementById('new-part-display').value || '').trim();
        if (!partName) {
            alert('Part name is required.');
            return;
        }
        if (!displayName) displayName = partName;
        var oldName = selectedPart;
        var p = parts[oldName];
        delete parts[oldName];
        var idx = partOrder.indexOf(oldName);
        if (idx >= 0) partOrder.splice(idx, 1);
        partOrder.push(partName);
        parts[partName] = p;
        p.mesh.userData.partName = partName;
        p.display = displayName;
        p.isNewPart = false;
        overlayNewParts.push({ name: partName, display: displayName });
        originalTransforms[partName] = originalTransforms[oldName] || { pos: p.group.position.clone(), rot: p.group.rotation.clone() };
        delete originalTransforms[oldName];
        selectedPart = partName;
        document.getElementById('sel-save-new-part-section').style.display = 'none';
        document.getElementById('sel-title').textContent = displayName;
        updatePartsList();
    });

    document.getElementById('btn-anchors').addEventListener('change', function() {
        updateAnchorVisibility();
    });

    document.getElementById('sel-anchors-toggle').addEventListener('change', function() {
        selectedPartAnchorsOn = this.checked;
        updateAnchorVisibility();
    });
    document.getElementById('btn-hide-component').addEventListener('click', function() {
        if (selectedPart && parts[selectedPart] && parts[selectedPart].visible) {
            togglePart(selectedPart);
        }
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

    function updateBuildResultText() {
        var el = document.getElementById('build-result-text');
        if (!el) return;
        var r = EMBEDDED_BUILD_RESULT;
        if (r && (r.success !== undefined || r.message)) {
            var msg = r.message || (r.success ? 'OK' : 'Failed');
            var parts = r.parts != null ? r.parts + ' parts' : '';
            var collisions = r.collisions != null && r.collisions > 0 ? ', ' + r.collisions + ' collisions' : '';
            var skipped = r.overlay_constraints_skipped != null && r.overlay_constraints_skipped > 0 ? ', ' + r.overlay_constraints_skipped + ' constraint(s) skipped' : '';
            el.textContent = msg + (parts ? ' (' + parts + collisions + skipped + ').' : '.');
        } else {
            el.textContent = '—';
        }
    }

    function loadEmbeddedPart(idx) {
        if (idx >= total) {
            loadingEl.style.display = 'none';
            fitCamera();
            updateBuildResultText();
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

    // ---- Route Editor ----
    // Coordinate helpers: tube_routes.json uses Z-up; THREE.js uses Y-up.
    // Z-up (x,y,z) -> Y-up (x, z, -y)   (load)
    // Y-up (x,y,z) -> Z-up (x, -z, y)   (save)
    function zupToYup(x, y, z) { return new THREE.Vector3(x, z, -y); }
    function yupToZup(v) { return [v.x, -v.z, v.y]; }

    var EMBEDDED_ROUTES = (typeof window.__VIEWER_ROUTES !== 'undefined') ? window.__VIEWER_ROUTES : null;

    // routeState[routeName] = { color, display, waypoints: [THREE.Vector3,...], isEndpoint:[bool,...] }
    var routeState = {};
    var routeLines = {};          // routeName -> THREE.Line
    var routeWpSpheres = {};      // routeName -> [THREE.Mesh,...]
    var routeObjects = new THREE.Group();  // separate group, not raycasted for parts
    routeObjects.visible = false;
    scene.add(routeObjects);

    var selectedRoute = null;     // routeName string
    var selectedWpIdx = -1;       // index within routeState[selectedRoute].waypoints
    var addWpMode = false;        // waiting for next click to place waypoint

    // Drag state for waypoint dragging
    var wpDragging = false;
    var wpDragPlane = new THREE.Plane();
    var wpDragOffset = new THREE.Vector3();
    var wpDragRaycaster = new THREE.Raycaster();
    var wpDragMouse = new THREE.Vector2();
    var wpDragModifier = null; // null | 'x' | 'y' | 'z'
    var wpDragOrigin = new THREE.Vector3();

    function routeColorHex(colorStr) {
        // Accept #rrggbb or css color names; fall back to 0x8ecae6
        if (!colorStr) return 0x8ecae6;
        return parseInt(colorStr.replace('#', '0x')) || 0x8ecae6;
    }

    function buildRouteGeometry(routeName) {
        var state = routeState[routeName];
        if (!state || state.waypoints.length < 2) return;
        var pts = state.waypoints;
        var positions = new Float32Array(pts.length * 3);
        for (var i = 0; i < pts.length; i++) {
            positions[i * 3]     = pts[i].x;
            positions[i * 3 + 1] = pts[i].y;
            positions[i * 3 + 2] = pts[i].z;
        }
        var line = routeLines[routeName];
        if (line) {
            line.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            line.geometry.setDrawRange(0, pts.length);
            line.geometry.attributes.position.needsUpdate = true;
        }
    }

    function buildRoutes() {
        if (!EMBEDDED_ROUTES) return;
        var routeNames = Object.keys(EMBEDDED_ROUTES);
        for (var ri = 0; ri < routeNames.length; ri++) {
            var rname = routeNames[ri];
            var rdata = EMBEDDED_ROUTES[rname];
            var wps = rdata.waypoints || [];
            var color = rdata.color || '#8ecae6';
            var display = rdata.display || rname;
            var colorInt = routeColorHex(color);

            // Convert Z-up waypoints to Y-up THREE.Vector3 array
            var wpVecs = [];
            var isEndpoint = [];
            for (var wi = 0; wi < wps.length; wi++) {
                var wp = wps[wi];
                wpVecs.push(zupToYup(wp[0], wp[1], wp[2]));
                isEndpoint.push(wi === 0 || wi === wps.length - 1);
            }
            routeState[rname] = { color: color, colorInt: colorInt, display: display, waypoints: wpVecs, isEndpoint: isEndpoint };

            // Build line
            var pts = wpVecs;
            var positions = new Float32Array(Math.max(pts.length, 2) * 3);
            for (var pi = 0; pi < pts.length; pi++) {
                positions[pi * 3]     = pts[pi].x;
                positions[pi * 3 + 1] = pts[pi].y;
                positions[pi * 3 + 2] = pts[pi].z;
            }
            var lineGeo = new THREE.BufferGeometry();
            lineGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            var lineMat = new THREE.LineBasicMaterial({ color: colorInt, linewidth: 2, depthTest: false });
            var line = new THREE.Line(lineGeo, lineMat);
            line.renderOrder = 990;
            line.userData.routeName = rname;
            routeLines[rname] = line;
            routeObjects.add(line);

            // Build waypoint spheres
            routeWpSpheres[rname] = [];
            for (var si = 0; si < wpVecs.length; si++) {
                var isEp = isEndpoint[si];
                var radius = isEp ? 1.5 : 2.5;
                var mat;
                if (isEp) {
                    mat = new THREE.MeshBasicMaterial({ color: 0x888888, depthTest: false, transparent: true, opacity: 0.7 });
                } else {
                    mat = new THREE.MeshBasicMaterial({ color: colorInt, depthTest: false, transparent: true, opacity: 0.75 });
                }
                var sphere = new THREE.Mesh(new THREE.SphereGeometry(radius, 12, 12), mat);
                sphere.position.copy(wpVecs[si]);
                sphere.renderOrder = 991;
                sphere.userData.routeName = rname;
                sphere.userData.wpIdx = si;
                sphere.userData.isEndpoint = isEp;
                routeWpSpheres[rname].push(sphere);
                routeObjects.add(sphere);
            }
        }
        buildRouteEditorUI();
    }

    function buildRouteEditorUI() {
        var editorBody = document.getElementById('route-editor-body');
        var noData = document.getElementById('route-no-data');
        if (!EMBEDDED_ROUTES || Object.keys(EMBEDDED_ROUTES).length === 0) {
            if (editorBody) editorBody.style.display = 'none';
            if (noData) noData.style.display = 'block';
            return;
        }
        if (editorBody) editorBody.style.display = '';
        if (noData) noData.style.display = 'none';

        var listSection = document.getElementById('route-list-section');
        if (!listSection) return;
        listSection.innerHTML = '';
        var routeNames = Object.keys(routeState);
        for (var ri = 0; ri < routeNames.length; ri++) {
            var rname = routeNames[ri];
            var state = routeState[rname];
            var row = document.createElement('div');
            row.style.cssText = 'display:flex;align-items:center;gap:6px;padding:3px 0;cursor:pointer;border-radius:4px;';
            row.setAttribute('data-route', rname);
            var dot = document.createElement('span');
            dot.style.cssText = 'display:inline-block;width:10px;height:10px;border-radius:50%;background:' + state.color + ';flex-shrink:0;';
            var label = document.createElement('span');
            label.style.cssText = 'font-size:11px;color:#e0e0e0;flex:1;';
            label.textContent = state.display + ' (' + state.waypoints.length + ' WP)';
            label.setAttribute('id', 'route-label-' + rname);
            row.appendChild(dot);
            row.appendChild(label);
            row.addEventListener('click', (function(name) {
                return function() { selectRoute(name); };
            })(rname));
            listSection.appendChild(row);
        }
    }

    function selectRoute(rname) {
        selectedRoute = rname;
        selectedWpIdx = -1;
        updateRouteWpPanel();
        // Highlight selected route label
        var routeNames = Object.keys(routeState);
        for (var ri = 0; ri < routeNames.length; ri++) {
            var el = document.getElementById('route-label-' + routeNames[ri]);
            if (el) el.style.color = routeNames[ri] === rname ? '#8ecae6' : '#e0e0e0';
        }
    }

    function selectWaypoint(rname, idx) {
        selectedRoute = rname;
        selectedWpIdx = idx;
        updateRouteWpPanel();
        highlightSelectedWp();
    }

    function highlightSelectedWp() {
        // Reset all spheres to base opacity, then brighten selected
        var routeNames = Object.keys(routeWpSpheres);
        for (var ri = 0; ri < routeNames.length; ri++) {
            var rn = routeNames[ri];
            var spheres = routeWpSpheres[rn];
            var state = routeState[rn];
            for (var si = 0; si < spheres.length; si++) {
                var isEp = state.isEndpoint[si];
                var isSelected = rn === selectedRoute && si === selectedWpIdx;
                var mat = spheres[si].material;
                if (isSelected) {
                    mat.color.setHex(0xffffff);
                    mat.opacity = 1.0;
                } else if (isEp) {
                    mat.color.setHex(0x888888);
                    mat.opacity = 0.7;
                } else {
                    mat.color.setHex(state.colorInt);
                    mat.opacity = 0.75;
                }
            }
        }
    }

    function updateRouteWpPanel() {
        var section = document.getElementById('route-wp-section');
        var routeNameEl = document.getElementById('route-wp-route-name');
        var labelEl = document.getElementById('route-wp-label');
        var xEl = document.getElementById('route-wp-x');
        var yEl = document.getElementById('route-wp-y');
        var zEl = document.getElementById('route-wp-z');
        var delBtn = document.getElementById('btn-route-del-wp');
        var hintEl = document.getElementById('route-wp-hint');
        if (!section) return;

        if (!selectedRoute || !routeState[selectedRoute] || selectedWpIdx < 0) {
            section.style.display = 'none';
            return;
        }
        section.style.display = 'block';
        var state = routeState[selectedRoute];
        var wp = state.waypoints[selectedWpIdx];
        if (!wp) { section.style.display = 'none'; return; }

        routeNameEl.textContent = 'Route: ' + state.display;
        labelEl.textContent = 'WP ' + selectedWpIdx + ': X=' + wp.x.toFixed(1) + ' Y=' + wp.y.toFixed(1) + ' Z=' + wp.z.toFixed(1);
        xEl.value = wp.x.toFixed(2);
        yEl.value = wp.y.toFixed(2);
        zEl.value = wp.z.toFixed(2);

        var isEp = state.isEndpoint[selectedWpIdx];
        delBtn.disabled = isEp;
        hintEl.textContent = isEp ? 'Endpoint — locked (connect point, not editable).' : 'Drag sphere or edit coords above.';
    }

    function applyWpInputChanges() {
        if (!selectedRoute || selectedWpIdx < 0) return;
        var state = routeState[selectedRoute];
        if (!state) return;
        var xEl = document.getElementById('route-wp-x');
        var yEl = document.getElementById('route-wp-y');
        var zEl = document.getElementById('route-wp-z');
        var x = parseFloat(xEl.value) || 0;
        var y = parseFloat(yEl.value) || 0;
        var z = parseFloat(zEl.value) || 0;
        state.waypoints[selectedWpIdx].set(x, y, z);
        var sphere = routeWpSpheres[selectedRoute][selectedWpIdx];
        if (sphere) sphere.position.set(x, y, z);
        buildRouteGeometry(selectedRoute);
        var labelEl = document.getElementById('route-wp-label');
        if (labelEl) labelEl.textContent = 'WP ' + selectedWpIdx + ': X=' + x.toFixed(1) + ' Y=' + y.toFixed(1) + ' Z=' + z.toFixed(1);
    }

    ['route-wp-x', 'route-wp-y', 'route-wp-z'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('change', applyWpInputChanges);
    });

    // Waypoint hover raycaster (separate from parts raycaster)
    var wpRaycaster = new THREE.Raycaster();
    var wpMouse = new THREE.Vector2();

    function getVisibleWpSpheres() {
        if (!routeObjects.visible) return [];
        var out = [];
        var routeNames = Object.keys(routeWpSpheres);
        for (var ri = 0; ri < routeNames.length; ri++) {
            var spheres = routeWpSpheres[routeNames[ri]];
            for (var si = 0; si < spheres.length; si++) {
                if (spheres[si].visible) out.push(spheres[si]);
            }
        }
        return out;
    }

    // Pointer-down: start waypoint drag
    var wpPointerDownPos = null;
    renderer.domElement.addEventListener('pointerdown', function(e) {
        if (!routeObjects.visible) return;
        if (e.button !== 0) return;
        wpPointerDownPos = { x: e.clientX, y: e.clientY };
        wpMouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        wpMouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        wpRaycaster.setFromCamera(wpMouse, cam);
        var spheres = getVisibleWpSpheres();
        var hits = wpRaycaster.intersectObjects(spheres);
        if (hits.length === 0) return;

        var hitSphere = hits[0].object;
        var rname = hitSphere.userData.routeName;
        var idx = hitSphere.userData.wpIdx;
        var isEp = hitSphere.userData.isEndpoint;

        selectWaypoint(rname, idx);

        if (!isEp) {
            // Set up drag plane perpendicular to camera at waypoint world pos
            wpDragging = true;
            wpDragOrigin.copy(hitSphere.position);
            var camDir = cam.getWorldDirection(new THREE.Vector3());
            wpDragPlane.setFromNormalAndCoplanarPoint(camDir, hitSphere.position);
            var intersectPt = new THREE.Vector3();
            wpRaycaster.ray.intersectPlane(wpDragPlane, intersectPt);
            wpDragOffset.subVectors(hitSphere.position, intersectPt);
            controls.enabled = false;
            e.stopPropagation();
        }
    });

    renderer.domElement.addEventListener('pointermove', function(e) {
        if (!wpDragging) return;
        if (!selectedRoute || selectedWpIdx < 0) return;
        wpDragMouse.x = (e.clientX / window.innerWidth) * 2 - 1;
        wpDragMouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
        wpRaycaster.setFromCamera(wpDragMouse, cam);
        var intersectPt = new THREE.Vector3();
        if (!wpRaycaster.ray.intersectPlane(wpDragPlane, intersectPt)) return;
        var newPos = intersectPt.add(wpDragOffset);

        // Axis constraints via keyboard modifier (read from current key state)
        if (wpDragModifier === 'x') { newPos.y = wpDragOrigin.y; newPos.z = wpDragOrigin.z; }
        else if (wpDragModifier === 'y') { newPos.x = wpDragOrigin.x; newPos.z = wpDragOrigin.z; }
        else if (wpDragModifier === 'z') { newPos.x = wpDragOrigin.x; newPos.y = wpDragOrigin.y; }

        var state = routeState[selectedRoute];
        state.waypoints[selectedWpIdx].copy(newPos);
        var sphere = routeWpSpheres[selectedRoute][selectedWpIdx];
        if (sphere) sphere.position.copy(newPos);
        buildRouteGeometry(selectedRoute);
        updateRouteWpPanel();
    });

    renderer.domElement.addEventListener('pointerup', function(e) {
        if (wpDragging) {
            wpDragging = false;
            controls.enabled = true;
        }
    });

    // Track modifier keys for axis-constrained drag
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT') return;
        if (e.shiftKey && !e.ctrlKey && !e.altKey) wpDragModifier = 'x';
        else if (!e.shiftKey && e.ctrlKey && !e.altKey) wpDragModifier = 'y';
        else if (!e.shiftKey && !e.ctrlKey && e.altKey) wpDragModifier = 'z';
    });
    document.addEventListener('keyup', function(e) {
        if (!e.shiftKey && !e.ctrlKey && !e.altKey) wpDragModifier = null;
    });

    // Click-to-place waypoint via Add WP mode
    var groundPlaneRoute = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    renderer.domElement.addEventListener('mouseup', function(e) {
        if (!addWpMode) return;
        if (!selectedRoute) { addWpMode = false; return; }
        // Only act on quick clicks (not drags)
        if (wpPointerDownPos && (Math.abs(e.clientX - wpPointerDownPos.x) > 5 || Math.abs(e.clientY - wpPointerDownPos.y) > 5)) return;

        var m = new THREE.Vector2(
            (e.clientX / window.innerWidth) * 2 - 1,
            -(e.clientY / window.innerHeight) * 2 + 1
        );
        var rc = new THREE.Raycaster();
        rc.setFromCamera(m, cam);

        // Try to hit a visible part mesh first
        var meshes = [];
        var pnames = Object.keys(parts);
        for (var pi = 0; pi < pnames.length; pi++) if (parts[pnames[pi]].visible) meshes.push(parts[pnames[pi]].mesh);
        var hits = rc.intersectObjects(meshes);
        var newPos;
        if (hits.length > 0) {
            newPos = hits[0].point.clone();
        } else {
            var gpt = new THREE.Vector3();
            if (rc.ray.intersectPlane(groundPlaneRoute, gpt)) {
                newPos = gpt.clone();
            } else {
                addWpMode = false;
                document.getElementById('btn-route-add-wp').classList.remove('active');
                return;
            }
        }

        var state = routeState[selectedRoute];
        var insertAfter = (selectedWpIdx >= 0) ? selectedWpIdx : state.waypoints.length - 2;
        if (insertAfter < 0) insertAfter = 0;
        // Clamp to not be after the last endpoint
        var lastIdx = state.waypoints.length - 1;
        if (insertAfter >= lastIdx) insertAfter = lastIdx - 1;
        if (insertAfter < 0) insertAfter = 0;

        var newIdx = insertAfter + 1;
        state.waypoints.splice(newIdx, 0, newPos.clone());
        state.isEndpoint.splice(newIdx, 0, false);

        // Rebuild spheres for this route
        rebuildRouteSpheres(selectedRoute);
        buildRouteGeometry(selectedRoute);
        buildRouteEditorUI();
        selectWaypoint(selectedRoute, newIdx);

        addWpMode = false;
        var addBtn = document.getElementById('btn-route-add-wp');
        if (addBtn) addBtn.classList.remove('active');
    }, false);

    function rebuildRouteSpheres(rname) {
        var state = routeState[rname];
        if (!state) return;
        // Remove old spheres
        var old = routeWpSpheres[rname] || [];
        for (var i = 0; i < old.length; i++) {
            routeObjects.remove(old[i]);
            old[i].geometry.dispose();
            old[i].material.dispose();
        }
        routeWpSpheres[rname] = [];
        for (var si = 0; si < state.waypoints.length; si++) {
            var isEp = state.isEndpoint[si];
            var radius = isEp ? 1.5 : 2.5;
            var mat;
            if (isEp) {
                mat = new THREE.MeshBasicMaterial({ color: 0x888888, depthTest: false, transparent: true, opacity: 0.7 });
            } else {
                mat = new THREE.MeshBasicMaterial({ color: state.colorInt, depthTest: false, transparent: true, opacity: 0.75 });
            }
            var sphere = new THREE.Mesh(new THREE.SphereGeometry(radius, 12, 12), mat);
            sphere.position.copy(state.waypoints[si]);
            sphere.renderOrder = 991;
            sphere.userData.routeName = rname;
            sphere.userData.wpIdx = si;
            sphere.userData.isEndpoint = isEp;
            routeWpSpheres[rname].push(sphere);
            routeObjects.add(sphere);
        }
    }

    // Route Editor panel buttons
    var btnRouteEditor = document.getElementById('btn-route-editor');
    if (btnRouteEditor) {
        btnRouteEditor.addEventListener('click', function() {
            var panel = document.getElementById('route-editor-panel');
            if (panel) {
                var vis = panel.style.display === 'block';
                panel.style.display = vis ? 'none' : 'block';
                this.classList.toggle('active', !vis);
            }
        });
    }

    var btnRoutesToggle = document.getElementById('btn-routes');
    if (btnRoutesToggle) {
        btnRoutesToggle.addEventListener('change', function() {
            routeObjects.visible = this.checked;
        });
    }

    var btnRouteAddWp = document.getElementById('btn-route-add-wp');
    if (btnRouteAddWp) {
        btnRouteAddWp.addEventListener('click', function() {
            if (!selectedRoute) { alert('Select a route first.'); return; }
            addWpMode = !addWpMode;
            this.classList.toggle('active', addWpMode);
            var hintEl = document.getElementById('route-wp-hint');
            if (hintEl) hintEl.textContent = addWpMode ? 'Click in viewport to place new waypoint...' : '';
        });
    }

    var btnRouteDelWp = document.getElementById('btn-route-del-wp');
    if (btnRouteDelWp) {
        btnRouteDelWp.addEventListener('click', function() {
            if (!selectedRoute || selectedWpIdx < 0) return;
            var state = routeState[selectedRoute];
            if (!state) return;
            if (state.isEndpoint[selectedWpIdx]) { alert('Cannot delete an endpoint waypoint.'); return; }
            state.waypoints.splice(selectedWpIdx, 1);
            state.isEndpoint.splice(selectedWpIdx, 1);
            rebuildRouteSpheres(selectedRoute);
            buildRouteGeometry(selectedRoute);
            buildRouteEditorUI();
            var newIdx = Math.min(selectedWpIdx, state.waypoints.length - 1);
            if (newIdx >= 0) {
                selectWaypoint(selectedRoute, newIdx);
            } else {
                selectedWpIdx = -1;
                updateRouteWpPanel();
            }
        });
    }

    var btnRouteSave = document.getElementById('btn-route-save');
    if (btnRouteSave) {
        btnRouteSave.addEventListener('click', function() {
            if (!EMBEDDED_ROUTES) { alert('No routes loaded.'); return; }
            var output = {};
            var routeNames = Object.keys(EMBEDDED_ROUTES);
            for (var ri = 0; ri < routeNames.length; ri++) {
                var rname = routeNames[ri];
                var orig = EMBEDDED_ROUTES[rname];
                var state = routeState[rname];
                if (!state) { output[rname] = orig; continue; }
                // Rebuild waypoints array in Z-up, keeping locked endpoints from original
                var newWps = [];
                for (var wi = 0; wi < state.waypoints.length; wi++) {
                    newWps.push(yupToZup(state.waypoints[wi]));
                }
                var routeCopy = {};
                for (var k in orig) if (orig.hasOwnProperty(k)) routeCopy[k] = orig[k];
                routeCopy.waypoints = newWps;
                output[rname] = routeCopy;
            }
            var json = JSON.stringify(output, null, 2);
            var blob = new Blob([json], { type: 'application/json' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'tube_routes.json';
            a.click();
            URL.revokeObjectURL(a.href);
        });
    }

    // Close button for route-editor-panel (data-closes already handled above for existing panels)
    // Wire the route editor panel's draggability via existing makeDraggable mechanism
    // (The panel uses the .draggable-panel class + .drag-handle so the existing loop handles it)

    // Initialize routes if data is available
    if (EMBEDDED_ROUTES && typeof EMBEDDED_ROUTES === 'object') {
        buildRoutes();
    } else {
        // Show "no data" message if panel is opened
        var noData = document.getElementById('route-no-data');
        var editorBody = document.getElementById('route-editor-body');
        if (noData) noData.style.display = 'block';
        if (editorBody) editorBody.style.display = 'none';
    }

})();
