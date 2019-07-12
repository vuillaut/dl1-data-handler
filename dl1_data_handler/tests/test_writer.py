import numpy as np
from ctapipe.calib.camera import gainselection
from dl1_data_handler.writer import DL1DataWriter
from ctapipe.utils import get_dataset_path
from ctapipe.io import event_source
from ctapipe.calib import CameraCalibrator

gain_selector = gainselection.ThresholdGainSelector(select_by_sample=True)


def test_writer_gain_selection():
    """
    test gain selection
    """
    # Let's generate a fake waveform from a camera of 3 samples and 10 pixels
    n_samples = 3
    w1 = np.transpose([np.concatenate([np.ones(5), 3 * np.ones(5)]) for i in range(n_samples)])
    w2 = np.transpose([10 * np.ones(10) for i in range(n_samples)])
    waveform = np.array([w1, w2])
    image = waveform.mean(axis=2)

    threshold = 2
    dld = DL1DataWriter()
    combined_image, combined_peakpos = dld.gain_selection(waveform, image, image, 'LSTCam', threshold)

    # with a threshold of 2, the 5 first pixels should be selected in the first channel and 5 others in the second \
    # channel

    np.testing.assert_array_equal(combined_image, np.array([1, 1, 1, 1, 1, 10, 10, 10, 10, 10]))


def test_data_writer():
    """
    Test _process_data
    """
    dld = DL1DataWriter()
    cal = CameraCalibrator()
    # dld._process_data([get_dataset_path('gamma_test_large.simtel.gz')], 'delete.tmp') #need good unit test file
    source = event_source(get_dataset_path('gamma_test_large.simtel.gz'))
    for event in source:
        cal.calibrate(event)
        for tel_id, dl1 in enumerate(event.dl1):
            camera = event.inst.subarray.tel[tel_id].camera
            waveform = event.r0.tel[tel_id].waveform
            image = event.dl1.tel[tel_id].image
            dld.combine_channels(event)