import tkinter as tk

from serial.tools.list_ports import comports

from interfacebuilder import make_base_frame, make_spaced_label, make_button, make_spacer, \
    make_updatable_label, InterfaceVariables, make_combobox, make_graph, make_thread, make_check_button, \
    make_named_spinbox, make_labeled_entry


def build_interface():
    top = tk.Tk()
    interface = InterfaceVariables()
    panel_port_selector(top, interface)
    panel_save_control(top, interface)
    panel_graph_control(top, interface)
    panel_graph_filter(top, interface)
    panel_graph_view(top, interface)

    return top, interface


def build_thread_interface(graph, interface: InterfaceVariables):
    def interface_manager():
        from time import sleep
        sleep(1)
        filter_state = interface.filter_data['state']
        graph_filters = interface.tk_data.get('graph')
        tk_vars = interface.tk_vars
        while interface.running.is_set():
            sleep(0.4)
            if not interface.running.is_set():
                return
            if interface.tk_vars.get('Lock axis').get() == 1:
                try:
                    x_min = float(tk_vars.get('x min').get())
                    x_max = float(tk_vars.get('x max').get())
                    y_min = float(tk_vars.get('y min').get())
                    y_max = float(tk_vars.get('y max').get())
                except ValueError:
                    continue
                if x_min == x_max:
                    x_min -= 1
                if y_min == y_max:
                    y_min -= 1
                graph.plot.set_xlim(x_min, x_max)
                graph.plot.set_ylim(y_min, y_max)
            if not interface.running.is_set():
                return
            if interface.tk_vars.get('Copy axis').get() == 1:
                x_min, x_max = graph.plot.get_xlim()
                y_min, y_max = graph.plot.get_ylim()
                tk_vars.get('x min').set(f'{x_min:.2f}')
                tk_vars.get('x max').set(f'{x_max:.2f}')
                tk_vars.get('y min').set(f'{y_min:.2f}')
                tk_vars.get('y max').set(f'{y_max:.2f}')
            if not interface.running.is_set():
                return
            for i, filter in enumerate(graph_filters):
                state = interface.tk_vars.get(filter).get() == 1
                filter_state.update({i: state})

    return interface_manager


def build_thread_graph(graph, interface: InterfaceVariables):
    def serial_graph():
        from time import sleep
        sleep(1)
        filter_state: dict = interface.filter_data['state']
        data: list = []
        queue = interface.arduino.queue_in
        while interface.running.is_set():
            sleep(0.1)
            if not interface.running.is_set():
                return
            if queue.empty():
                sleep(0.5)
                continue
            while not queue.empty():
                serial_data = queue.get()
                for index, value in enumerate(serial_data):
                    try:
                        data[index].append(value)
                    except IndexError:
                        data.append([value])
            graph_data: dict = {}
            for index, values in enumerate(data):
                if index in filter_state and filter_state[index] is True:
                    graph_data.update({index: values[-200:]})
            graph.update(graph_data)

    return serial_graph


def panel_graph_control(base, interface: InterfaceVariables):
    frame = make_base_frame(base)
    make_spacer(frame, 2)
    make_spaced_label(frame, 'Configurator')
    make_check_button(frame, interface.tk_vars, 'Lock axis')
    make_check_button(frame, interface.tk_vars, 'Copy axis')

    make_spaced_label(frame, 'X-axis')
    interface.tk_vars['x min'] = make_named_spinbox(frame, 'Min')
    interface.tk_vars['x max'] = make_named_spinbox(frame, 'Max')
    make_spaced_label(frame, 'Y-axis')
    interface.tk_vars['y min'] = make_named_spinbox(frame, 'Min')
    interface.tk_vars['y max'] = make_named_spinbox(frame, 'Max')


def panel_graph_filter(base, interface: InterfaceVariables):
    interface.tk_data['graph'] = button_list = [
        'Pressure raw', 'Pressure filtered', 'Pressure average',
        'Pressure differential', 'Pressure filtered - average',
        'Pressure raw - average', 'Breath BPM', 'Breath BPM filtered',
        'Breath BPM smooth', 'Breath peak detection',
        'Heart beat signal', 'Heart beat peak', 'Heart beat BPM'
    ]

    frame = make_base_frame(base)
    make_spacer(frame, 2)
    make_spaced_label(frame, 'Graph line filters:')
    for name in button_list:
        make_check_button(frame, interface.tk_vars, name)
    interface.filter_data['state'] = {}


def panel_graph_view(base, interface: InterfaceVariables):
    frame = make_base_frame(base)
    frame.config(width=2000)
    graph = make_graph(frame)

    make_thread(build_thread_graph(graph, interface), interface, 'Serial graph')
    make_thread(build_thread_interface(graph, interface), interface, 'Interface manager')


def panel_port_selector(base, interface: InterfaceVariables):
    def connect_command():
        arduino = interface.arduino
        port = combobox.get()
        success = arduino.connect(port)
        if success is True:
            success = 'Connected'
        elif success is False:
            success = 'Already connected'
        else:
            success = 'Not connected'
        interface.tk_vars.get('success').set(success)

    def disconnect_command():
        arduino = interface.arduino
        port = arduino.serial.name
        success = arduino.disconnect()
        if success is True:
            success = 'Disconnected'
        elif success is False:
            success = 'Not connected'
        else:  # This line should/will never happen
            success = 'Fatal error'
        interface.tk_vars.get('success').set(success)

    def reconnect_command():
        arduino = interface.arduino
        port = arduino.serial.name
        success1 = arduino.disconnect()
        success2 = arduino.connect(port)
        if success1 and success2 is True:
            success = 'Reconnected'
        elif success1 and success2 is False:
            success = 'Connected'
        else:
            success = 'Not connected'
        interface.tk_vars.get('success').set(success)

    def refresh_command():
        text = ''
        ports = []
        for port in comports():
            name = str(port.device)
            ports += [name]
            text += name + '\n'
        if len(ports) == 0:
            text += 'None available\n'
            ports += ['None']
        interface.tk_data['port'] = ports
        interface.tk_vars.get('ports').set(text)

    def send_command():
        data = entry.get()
        entry.delete(0, tk.END)
        interface.arduino.queue_out.put(data)

    frame = make_base_frame(base)
    make_spacer(frame, 2)
    make_spaced_label(frame, 'Selectable ports:')
    make_updatable_label(frame, interface.tk_vars, 'ports')
    interface.tk_vars.get('ports').set('Please refresh list\n')

    make_spacer(frame, 20)  # Give some space for those dangerous buttons
    make_updatable_label(frame, interface.tk_vars, 'success')
    combobox = make_combobox(frame, interface.tk_data, 'port')
    make_button(frame, refresh_command, 'Refresh')
    make_button(frame, connect_command, 'Connect')
    make_button(frame, disconnect_command, 'Disconnect')
    make_button(frame, reconnect_command, 'Reconnect')

    make_spacer(frame, 20)  # Give some space for those dangerous buttons
    entry = make_labeled_entry(frame, 'Send serial:')
    make_button(frame, send_command, 'Send')
    make_spacer(frame, 20)  # Give some space for those dangerous buttons


def panel_save_control(base, interface: InterfaceVariables):
    def save_command():
        pass

    def start_command():
        pass

    def pause_command():
        pass

    frame = make_base_frame(base)
    make_spacer(frame, 2)
    entry = make_labeled_entry(frame, 'File name:')
    make_spaced_label(frame, 'Recording:')
    make_button(frame, start_command, 'Start')
    make_button(frame, pause_command, 'Pause')
    make_button(frame, save_command, 'Save')
    make_spacer(frame, 20)  # Give some space for those dangerous buttons
    make_check_button(frame, interface.tk_vars, 'Auto-Save')
    make_check_button(frame, interface.tk_vars, 'File append')
    make_check_button(frame, interface.tk_vars, 'File overwrite')
    make_spacer(frame, 20)  # Give some space for those dangerous buttons


def main():
    root, interface = build_interface()
    interface.start_threads()
    root.mainloop()
    interface.stop_threads()


if __name__ == '__main__':
    main()
