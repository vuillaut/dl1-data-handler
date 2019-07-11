import numpy as np
from ctapipe.calib.camera import gainselection
from dl1_data_handler.writer import gain_selection, DL1DataWriter
from ctapipe.utils import get_dataset_path

gain_selector = gainselection.ThresholdGainSelector(select_by_sample=True)


def test_gain_selection():
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
    combined_image, combined_peakpos = gain_selection(waveform, image, image, 'LSTCam', threshold)

    # with a threshold of 2, the 5 first pixels should be selected in the first channel and 5 others in the second \
    # channel

    np.testing.assert_array_equal(combined_image, np.array([1, 1, 1, 1, 1, 10, 10, 10, 10, 10]))


def test_data_writer():
    dld = DL1DataWriter()
    dld._process_data([get_dataset_path('gamma_test_large.simtel.gz')], 'delete.tmp')