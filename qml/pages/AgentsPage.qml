import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import LlamaCode 1.0

Item {
    id: root
    property string selectedId: ""
    property var edit: ({})
    property var revisionRows: []
    property var feedbackRows: []
    property var metricRows: ({})

    function selectAgent(id) {
        selectedId = id || ""
        edit = selectedId ? App.agentDefinitions.get(selectedId) : ({})
        nameField.text = edit.name || ""
        descriptionField.text = edit.description || ""
        instructionsField.text = edit.instructions || ""
        profileField.text = edit.profileId || ""
        launchField.text = edit.launchProfileId || ""
        workspaceField.text = edit.workspaceId || ""
        taskField.text = (edit.taskIds || []).join(", ")
        skillsField.text = (edit.skillIds || []).join(", ")
        revisionRows = selectedId ? App.agentDefinitions.revisions(selectedId) : []
        feedbackRows = selectedId ? App.agentDefinitions.pendingFeedback(selectedId) : []
        metricRows = selectedId ? App.agentDefinitionMetrics(selectedId) : ({})
    }

    function splitIds(text) {
        return text.split(",").map(v => v.trim()).filter(v => v.length > 0)
    }

    function saveAgent(reason) {
        const id = App.agentDefinitions.save(selectedId, {
            name: nameField.text, description: descriptionField.text,
            instructions: instructionsField.text, profileId: profileField.text,
            launchProfileId: launchField.text, workspaceId: workspaceField.text,
            taskIds: splitIds(taskField.text), skillIds: splitIds(skillsField.text),
            mcpServers: edit.mcpServers || [], toolPermissions: edit.toolPermissions || {},
            triggerIds: edit.triggerIds || []
        }, reason || "Edición desde Agentes")
        if (id) selectAgent(id)
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        Rectangle {
            Layout.preferredWidth: 260
            Layout.fillHeight: true
            color: Theme.surfaceBg
            radius: 8
            border.color: Theme.borderColor
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: 8
                RowLayout {
                    Text { text: "Agentes"; color: Theme.textPrimary; font.pixelSize: 19; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Button {
                        text: "+"
                        onClicked: {
                            root.selectedId = ""
                            root.edit = ({})
                            root.selectAgent("")
                            nameField.forceActiveFocus()
                        }
                    }
                }
                ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    model: App.agentDefinitions
                    clip: true
                    delegate: ItemDelegate {
                        required property string id
                        required property string name
                        required property int currentRevision
                        width: ListView.view.width
                        highlighted: root.selectedId === id
                        text: name + "  · r" + currentRevision
                        onClicked: root.selectAgent(id)
                    }
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ColumnLayout {
                width: Math.max(620, parent.width - 16)
                spacing: 10

                Text { text: selectedId ? "Definición persistente" : "Nuevo agente"; color: Theme.textPrimary; font.pixelSize: 20; font.bold: true }
                TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Nombre" }
                TextField { id: descriptionField; Layout.fillWidth: true; placeholderText: "Descripción y propósito" }
                TextArea {
                    id: instructionsField; Layout.fillWidth: true; Layout.preferredHeight: 130
                    placeholderText: "Instrucciones permanentes del agente"; wrapMode: TextEdit.Wrap
                }
                GridLayout {
                    Layout.fillWidth: true; columns: 2; columnSpacing: 8; rowSpacing: 8
                    TextField { id: profileField; Layout.fillWidth: true; placeholderText: "AgentProfile ID" }
                    TextField { id: launchField; Layout.fillWidth: true; placeholderText: "LaunchProfile ID" }
                    TextField { id: workspaceField; Layout.fillWidth: true; placeholderText: "Workspace ID" }
                    TextField { id: taskField; Layout.fillWidth: true; placeholderText: "Task IDs, separados por coma" }
                    TextField { id: skillsField; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: "Skill IDs, separados por coma" }
                }
                RowLayout {
                    Button { text: "Guardar nueva revisión"; enabled: nameField.text.trim().length > 0; onClicked: root.saveAgent() }
                    Button {
                        text: App.activeAgentDefinitionId === selectedId ? "Activo" : "Activar"
                        enabled: selectedId.length > 0 && App.activeAgentDefinitionId !== selectedId
                        onClicked: App.activateAgentDefinition(selectedId)
                    }
                    Button {
                        text: "Duplicar"; enabled: selectedId.length > 0
                        onClicked: root.selectAgent(App.agentDefinitions.duplicate(selectedId))
                    }
                    Button {
                        text: "Eliminar"; enabled: selectedId.length > 0
                        onClicked: { App.agentDefinitions.remove(selectedId); root.selectAgent("") }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }
                Text { text: "Resultado operativo"; color: Theme.textPrimary; font.pixelSize: 16; font.bold: true }
                Text {
                    Layout.fillWidth: true; color: Theme.textSecondary; wrapMode: Text.Wrap
                    text: "Corridas: " + (metricRows.runs || 0)
                          + " · éxito: " + Number(metricRows.successRate || 0).toFixed(1) + "%"
                          + " · tokens: " + Number((metricRows.promptTokens || 0)
                                                  + (metricRows.generatedTokens || 0)).toFixed(0)
                }

                Text { text: "Feedback supervisado"; color: Theme.textPrimary; font.pixelSize: 16; font.bold: true }
                RowLayout {
                    TextField { id: feedbackField; Layout.fillWidth: true; placeholderText: "Corrección que querés convertir en instrucción" }
                    Button {
                        text: "Proponer"; enabled: selectedId.length > 0 && feedbackField.text.trim().length > 0
                        onClicked: {
                            App.agentDefinitions.proposeFeedback(selectedId, feedbackField.text, "agent")
                            feedbackField.clear()
                            root.selectAgent(selectedId)
                        }
                    }
                }
                Repeater {
                    model: feedbackRows
                    delegate: RowLayout {
                        Layout.fillWidth: true
                        Text { Layout.fillWidth: true; text: modelData.feedback; color: Theme.textSecondary; wrapMode: Text.Wrap }
                        Button {
                            text: "Aprobar"
                            onClicked: { App.agentDefinitions.approveFeedback(modelData.id); root.selectAgent(selectedId) }
                        }
                        Button {
                            text: "Rechazar"
                            onClicked: { App.agentDefinitions.rejectFeedback(modelData.id); root.selectAgent(selectedId) }
                        }
                    }
                }

                Text { text: "Historial de configuración"; color: Theme.textPrimary; font.pixelSize: 16; font.bold: true }
                Repeater {
                    model: revisionRows.slice().reverse()
                    delegate: RowLayout {
                        Layout.fillWidth: true
                        Text {
                            Layout.fillWidth: true; color: Theme.textSecondary
                            text: "r" + modelData.number + " · " + modelData.reason + " · " + modelData.createdAt
                        }
                        Button {
                            text: "Restaurar"; enabled: modelData.number !== edit.currentRevision
                            onClicked: { App.agentDefinitions.restoreRevision(selectedId, modelData.number); root.selectAgent(selectedId) }
                        }
                    }
                }

                Text { text: "Triggers normalizados"; color: Theme.textPrimary; font.pixelSize: 16; font.bold: true }
                Text {
                    Layout.fillWidth: true; color: Theme.textSecondary; wrapMode: Text.Wrap
                    text: "Filesystem se vigila localmente. Webhook y appEvent usan el mismo contrato dispatchEvent(type, payload)."
                }
                RowLayout {
                    ComboBox { id: triggerType; model: ["filesystem", "webhook", "appEvent"] }
                    TextField { id: triggerValue; Layout.fillWidth: true; placeholderText: triggerType.currentText === "filesystem" ? "Ruta" : "Clave o nombre de evento" }
                    TextField { id: triggerTask; Layout.fillWidth: true; placeholderText: "Task ID" }
                    Button {
                        text: "Agregar"
                        enabled: selectedId.length > 0 && triggerValue.text.length > 0 && triggerTask.text.length > 0
                        onClicked: {
                            const cfg = triggerType.currentText === "filesystem"
                                ? {path: triggerValue.text}
                                : (triggerType.currentText === "webhook"
                                   ? {key: triggerValue.text} : {name: triggerValue.text})
                            const tid = App.triggerManager.save("", {
                                name: triggerType.currentText + ": " + triggerValue.text,
                                agentId: selectedId, taskId: triggerTask.text,
                                type: triggerType.currentText, enabled: true,
                                debounceMs: 1500, config: cfg
                            })
                            if (tid) {
                                const a = App.agentDefinitions.get(selectedId)
                                const ids = (a.triggerIds || []).slice()
                                ids.push(tid); a.triggerIds = ids
                                App.agentDefinitions.save(selectedId, a, "Trigger agregado")
                                triggerValue.clear(); triggerTask.clear(); root.selectAgent(selectedId)
                            }
                        }
                    }
                }
                Repeater {
                    model: App.triggerManager
                    delegate: RowLayout {
                        required property string id
                        required property string agentId
                        required property string name
                        visible: agentId === root.selectedId
                        Layout.fillWidth: visible
                        Text { Layout.fillWidth: true; text: name; color: Theme.textSecondary }
                        Button {
                            text: "Eliminar"
                            onClicked: { App.triggerManager.remove(id); root.selectAgent(root.selectedId) }
                        }
                    }
                }
                Item { Layout.preferredHeight: 20 }
            }
        }
    }
}
