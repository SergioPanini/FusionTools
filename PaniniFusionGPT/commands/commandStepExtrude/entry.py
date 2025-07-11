import adsk.core, adsk.fusion
import traceback
import os
from ...lib import fusionAddInUtils as futil
from ... import config

app = adsk.core.Application.get()
ui = app.userInterface if app else None

CMD_ID = 'cmdStepExtrude'
CMD_NAME = 'Ступенчатое выдавливание'
CMD_Description = 'Создание серии ступенчатых выдавливаний по профилям на разных скетчах.'
IS_PROMOTED = True
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')
local_handlers = []

MAX_STEPS = 30

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
    defaultLengthUnits = app.activeProduct.unitsManager.defaultLengthUnits
    # Число ступеней
    steps_input = inputs.addIntegerSpinnerCommandInput('steps_count', 'Число ступеней', 1, MAX_STEPS, 1, 2)
    # Первый шаг
    first_offset_input = inputs.addValueInput('first_offset', 'Первый шаг (offset)', defaultLengthUnits, adsk.core.ValueInput.createByString('100'))
    # Общий шаг
    step_input = inputs.addValueInput('step', 'Общий шаг', defaultLengthUnits, adsk.core.ValueInput.createByString('150'))
    # Толщина ступени
    thickness_input = inputs.addValueInput('thickness', 'Толщина ступени', defaultLengthUnits, adsk.core.ValueInput.createByString('40'))
    # Создаём поля для ступеней начиная с 1
    for i in range(MAX_STEPS):
        sel = inputs.addSelectionInput(f'profile_{i}', f'Профили для ступени {i+1}', 'Выберите один или несколько профилей на любом скетче')
        sel.addSelectionFilter('Profiles')
        sel.setSelectionLimits(0, 0)
        sel.isMultiSelectEnabled = True
        sel.isVisible = i < 2
    # Обработчики событий
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)

def command_input_changed(args: adsk.core.InputChangedEventArgs):
    inputs = args.inputs
    changed = args.input
    if changed.id == 'steps_count':
        count = changed.value
        for i in range(MAX_STEPS):
            inp = inputs.itemById(f'profile_{i}')
            if inp:
                inp.isVisible = i < count

def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} Command Execute Event')
    inputs = args.command.commandInputs
    try:
        steps_count = inputs.itemById('steps_count').value
        ui.messageBox(f'steps_count: {steps_count}')
        first_offset = inputs.itemById('first_offset').value
        step = inputs.itemById('step').value
        thickness = inputs.itemById('thickness').value
        design = app.activeProduct
        root = design.rootComponent
        extrudes = root.features.extrudeFeatures
        for i in range(steps_count):
            extrudes = root.features.extrudeFeatures
            profile_input = inputs.itemById(f'profile_{i}')
            if profile_input.selectionCount == 0:
                continue
            
            offset = first_offset + (i) * step

            height = thickness
            profiles_collection = adsk.core.ObjectCollection.create()
            for j in range(profile_input.selectionCount):
                profiles_collection.add(profile_input.selection(j).entity)
            ext_input = extrudes.createInput(profiles_collection, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-height))
            extrude = extrudes.add(ext_input)
            for b in extrude.bodies:
                b.name = f'step_{i+1}'
            try:
                for b in extrude.bodies:
                    sketch = profile_input.selection(0).entity.parentSketch
                    normal = sketch.referencePlane.geometry.normal
                    vector = adsk.core.Vector3D.create(normal.x * offset, normal.y * offset, normal.z * offset)
                    move_feats = root.features.moveFeatures
                    bodies_collection = adsk.core.ObjectCollection.create()
                    bodies_collection.add(b)
                    transform = adsk.core.Matrix3D.create()
                    transform.translation = vector
                    move_input = move_feats.createInput(bodies_collection, transform)
                    move_feats.add(move_input)
            except Exception as e:
                ui.messageBox(f'Ошибка перемещения: {e}')
        ui.messageBox('Ступенчатое выдавливание завершено!')
    except Exception as e:
        ui.messageBox(f'Ошибка: {e}\n{traceback.format_exc()}')

def command_destroy(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME} Command Destroy Event')
    global local_handlers
    local_handlers = [] 