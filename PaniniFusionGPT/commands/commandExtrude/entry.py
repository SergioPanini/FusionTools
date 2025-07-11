import adsk.core
import adsk.fusion
import os
from ...lib import fusionAddInUtils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface

CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdExtrude'
CMD_NAME = 'Выдавливание по профилям'
CMD_Description = 'Создать выдавливание выбранных замкнутых кривых на заданную высоту.'
IS_PROMOTED = True
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')
local_handlers = []

def start():
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)
    futil.add_handler(cmd_def.commandCreated, command_created)
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
    control.isPromoted = IS_PROMOTED

def stop():
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    if command_control:
        command_control.deleteMe()
    if command_definition:
        command_definition.deleteMe()

def command_created(args: adsk.core.CommandCreatedEventArgs):
    futil.log(f'{CMD_NAME} Command Created Event')
    inputs = args.command.commandInputs
    # Множественный выбор профилей (замкнутых кривых)
    profiles_input = inputs.addSelectionInput('profiles', 'Профили', 'Выберите замкнутые кривые (профили)')
    profiles_input.addSelectionFilter('Profiles')
    profiles_input.setSelectionLimits(0, 0)  # 0,0 = неограниченно
    profiles_input.isMultiSelectEnabled = True
    # Ввод высоты выдавливания
    defaultLengthUnits = app.activeProduct.unitsManager.defaultLengthUnits
    default_value = adsk.core.ValueInput.createByString('1')
    inputs.addValueInput('extrude_height', 'Высота выдавливания', defaultLengthUnits, default_value)
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} Command Execute Event')
    inputs = args.command.commandInputs
    profiles_input = inputs.itemById('profiles')
    height_input = inputs.itemById('extrude_height')
    height = height_input.value
    if profiles_input.selectionCount == 0:
        ui.messageBox('Не выбраны профили!')
        return
    try:
        design = app.activeProduct
        root = design.rootComponent
        extrudes = root.features.extrudeFeatures
        # Собираем все выбранные профили в ObjectCollection
        profiles_collection = adsk.core.ObjectCollection.create()
        for i in range(profiles_input.selectionCount):
            profile = profiles_input.selection(i).entity
            profiles_collection.add(profile)
        ext_input = extrudes.createInput(profiles_collection, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(height)
        ext_input.setDistanceExtent(False, distance)
        extrudes.add(ext_input)
        ui.messageBox('Выдавливание завершено!')
    except Exception as e:
        ui.messageBox(f'Ошибка: {e}')

def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} Command Destroy Event')
    global local_handlers
    local_handlers = [] 