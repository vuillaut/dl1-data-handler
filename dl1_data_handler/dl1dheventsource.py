from astropy import units as u
from astropy.coordinates import Angle
from ctapipe.io.eventsource import EventSource
from ctapipe.io.containers import DataContainer
from ctapipe.instrument import (
    TelescopeDescription,
    SubarrayDescription,
    OpticsDescription,
    CameraGeometry,
)

import numpy as np
import warnings

__all__ = ['DL1DHEventSource']


class DL1DHEventSource(EventSource):
    """
    EventSource for the dl1_data_handler file format.

    This class utilises `pytables` to read the DL1 file, and stores the
    information into the event containers.
    """
    _count = 0

    def __init__(self, config=None, parent=None, **kwargs):
        super().__init__(config=config, parent=parent, **kwargs)

        try:
            import tables
        except ImportError:
            msg = "The `pytables` python module is required to access DL1DH data"
            self.log.error(msg)
            raise

        self.tables = tables

        if DL1DHEventSource._count > 0:
            self.log.warning("Only one DL1DH event_source allowed at a time. "
                             "Previous DL1DH file will be closed.")
            # self.tables.close()
        DL1DHEventSource._count += 1

        self.metadata['is_simulation'] = True

    @staticmethod
    def is_compatible(file_path):
        '''This class should never be chosen in event_source()'''
        return False

    # def __exit__(self, exc_type, exc_val, exc_tb):
    #     DL1DHEventSource._count -= 1
    #     self.pyhessio.close_file()

    def _generator(self):
        with self.tables.open_file(self.input_url) as file:
            # the container is initialized once, and data is replaced within
            # it after each yield
            counter = 0
            eventstream = file.root.Events
            data = DataContainer()
            data.meta['origin'] = "dl1_data_handler"

            data.meta['input_url'] = self.input_url
            data.meta['max_events'] = self.max_events

            tel_types = set(file.root.Array_Information[:]['type'])
            run_array_direction = file.root._v_attrs['run_array_direction']
            # array_alt_pointing = run_array_direction[1] * u.rad
            # array_az_pointing = run_array_direction[0] * u.rad

            tel_ids = {}
            for tel_type in tel_types:
                tel_ids[tel_type] = file.root.Array_Information[file.root.Array_Information[:]['type'] == tel_type]['id']

            for event in eventstream:

                if counter == 0:
                    # subarray info is only available when an event is loaded,
                    # so load it on the first event.
                    data.inst.subarray = self._build_subarray_info(file)

                obs_id = event['obs_id']
                event_id = event['event_id']
                tels_with_data = np.concatenate([tel_ids[tel_type][event[tel_type.decode() + '_indices'].nonzero()]
                                                 for tel_type in tel_types])
                data.count = counter
                data.r0.obs_id = obs_id
                data.r0.event_id = event_id
                data.r0.tels_with_data = tels_with_data
                data.r1.obs_id = obs_id
                data.r1.event_id = event_id
                data.r1.tels_with_data = tels_with_data
                data.dl0.obs_id = obs_id
                data.dl0.event_id = event_id
                data.dl0.tels_with_data = tels_with_data

                # handle telescope filtering by taking the intersection of
                # tels_with_data and allowed_tels
                if len(self.allowed_tels) > 0:
                    selected = tels_with_data & self.allowed_tels
                    if len(selected) == 0:
                        continue  # skip event
                    data.r0.tels_with_data = selected
                    data.r1.tels_with_data = selected
                    data.dl0.tels_with_data = selected

                # data.trig.tels_with_trigger = (file.
                #                                get_central_event_teltrg_list()) # info not kept

                # time_s, time_ns = file.get_central_event_gps_time()
                # data.trig.gps_time = Time(time_s * u.s, time_ns * u.ns,
                #                           format='unix', scale='utc')
                data.mc.energy = event['mc_energy'] * u.TeV
                data.mc.alt = Angle(event['alt'], u.rad)
                data.mc.az = Angle(event['az'], u.rad)
                data.mc.core_x = event['core_x'] * u.m
                data.mc.core_y = event['core_y'] * u.m
                first_int = event['h_first_int'] * u.m
                data.mc.h_first_int = first_int
                data.mc.x_max = event['x_max'] * u.g / (u.cm**2)
                data.mc.shower_primary_id = event['shower_primary_id']

                # mc run header data
                self._build_mcheader(file, data)

                # this should be done in a nicer way to not re-allocate the
                # data each time (right now it's just deleted and garbage
                # collected)

                data.r0.tel.clear()
                data.r1.tel.clear()
                data.dl0.tel.clear()
                data.dl1.tel.clear()
                data.mc.tel.clear()  # clear the previous telescopes

                for tel_type in tel_types:
                    idxs = event[tel_type.decode() + '_indices']
                    for idx in idxs[idxs > 0]:
                        tel_id = tel_ids[tel_type][np.where(idxs == idx)[0][0]]
                        charge = file.root[tel_type.decode()][idx]['charge']
                        peakpos = file.root[tel_type.decode()][idx]['peakpos']

                        data.dl1.tel[tel_id].image = charge
                        data.dl1.tel[tel_id].pulse_time = peakpos

                yield data
                counter += 1

        return

    def _build_subarray_info(self, file):
        """
        constructs a SubarrayDescription object from the info in an DL1 file

        Parameters
        ----------
        file: pytables opened File

        Returns
        -------
        SubarrayDescription :
            instrumental information
        """

        subarray = SubarrayDescription("MonteCarloArray")

        for tel in file.root.Array_Information:
            tel_id = tel['id']
            tel_type = tel['type']
            tel_info = file.root.Telescope_Type_Information[file.root.Telescope_Type_Information[:]['type'] == tel_type][0]
            subarray.tels[tel_id] = self._build_telescope_description(tel_info)
            tel_pos = u.Quantity([tel['x'], tel['y'], tel['z']], u.m)
            subarray.positions[tel_id] = tel_pos

        return subarray


    def _build_telescope_description(self, tel_info):

        camera_name = tel_info['camera'].decode()
        optics_name = tel_info['optics'].decode()
        try:
            CameraGeometry.from_name(camera_name)
        except ValueError:
            warnings.warn(f'Unkown camera name {camera_name}')
        try:
            OpticsDescription.from_name(optics_name)
        except ValueError:
            warnings.warn(f'Unkown optics name {optics_name}')


        return TelescopeDescription.from_name(optics_name, camera_name)


    def _build_mcheader(self, file, data):
        """
        Read the mcheader data from the DL1 file and update the data container

        Parameters
        ----------
        file: pytables opened file
        data: `ctapipe.io.containers.DataContainer`
        """

        for k in data.mcheader.keys():
            try:
                data.mcheader[k] = file.root._v_attrs[k]
            except:
                warnings.warn(f"item {k} does not exist in the file attributes")



'''
### TODO:
- deal with close file (self.file.close() ?)
- make a version working with ctapipe master (pulse_time)
- unit test or check that a converted simtel file give the same info in ctapipe containers
'''