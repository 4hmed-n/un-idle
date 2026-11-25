from unittest.mock import patch, MagicMock
import capture_guard


def test_capture_exclusion_non_windows():
    with patch("capture_guard.platform.system", return_value="Linux"):
        assert capture_guard.get_windows_build() is None
        assert capture_guard.is_windows_capture_exclusion_supported() is False


def test_windows_build_threshold():
    with patch("capture_guard.get_windows_build", return_value=18363):
        assert capture_guard.is_windows_capture_exclusion_supported() is False

    with patch("capture_guard.get_windows_build", return_value=19041):
        assert capture_guard.is_windows_capture_exclusion_supported() is True

    with patch("capture_guard.get_windows_build", return_value=26100):
        assert capture_guard.is_windows_capture_exclusion_supported() is True


def test_apply_capture_exclusion_mocked_ctypes():
    """Test SetWindowDisplayAffinity call arguments and return handling."""
    mock_window = MagicMock()
    mock_window.winfo_id.return_value = 12345
    mock_window.update_idletasks.return_value = None
    
    mock_user32 = MagicMock()
    mock_user32.GetAncestor.return_value = 67890  # Root HWND
    mock_user32.SetWindowDisplayAffinity.return_value = 1  # Success
    
    with patch("capture_guard.is_windows_capture_exclusion_supported", return_value=True), \
         patch("capture_guard.ctypes.windll.user32", mock_user32):
        
        # Test enabling capture exclusion
        result = capture_guard.apply_capture_exclusion(mock_window, enabled=True)
        assert result is True
        mock_user32.GetAncestor.assert_called_once_with(12345, capture_guard.GA_ROOT)
        mock_user32.SetWindowDisplayAffinity.assert_called_once_with(67890, capture_guard.WDA_EXCLUDEFROMCAPTURE)
        
        # Reset mocks
        mock_user32.reset_mock()
        
        # Test disabling capture exclusion
        result = capture_guard.apply_capture_exclusion(mock_window, enabled=False)
        assert result is True
        mock_user32.SetWindowDisplayAffinity.assert_called_once_with(67890, capture_guard.WDA_NONE)


def test_apply_capture_exclusion_fallback_hwnd():
    """Test fallback to winfo_id when GetAncestor returns 0."""
    mock_window = MagicMock()
    mock_window.winfo_id.return_value = 12345
    
    mock_user32 = MagicMock()
    mock_user32.GetAncestor.return_value = 0  # No root ancestor found
    mock_user32.SetWindowDisplayAffinity.return_value = 1
    
    with patch("capture_guard.is_windows_capture_exclusion_supported", return_value=True), \
         patch("capture_guard.ctypes.windll.user32", mock_user32):
        
        result = capture_guard.apply_capture_exclusion(mock_window, enabled=True)
        assert result is True
        # Should fall back to using winfo_id directly
        mock_user32.SetWindowDisplayAffinity.assert_called_once_with(12345, capture_guard.WDA_EXCLUDEFROMCAPTURE)


def test_apply_capture_exclusion_unsupported_platform():
    """Test that unsupported platform returns False without attempting ctypes calls."""
    mock_window = MagicMock()
    
    with patch("capture_guard.is_windows_capture_exclusion_supported", return_value=False):
        result = capture_guard.apply_capture_exclusion(mock_window, enabled=True)
        assert result is False
        mock_window.update_idletasks.assert_not_called()


def test_apply_capture_exclusion_exception_handling():
    """Test that exceptions during ctypes calls are caught and return False."""
    mock_window = MagicMock()
    mock_window.winfo_id.side_effect = Exception("Window error")
    
    with patch("capture_guard.is_windows_capture_exclusion_supported", return_value=True):
        result = capture_guard.apply_capture_exclusion(mock_window, enabled=True)
        assert result is False
