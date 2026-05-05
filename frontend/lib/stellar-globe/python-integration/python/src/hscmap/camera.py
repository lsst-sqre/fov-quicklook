import time
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

from .angle import Angle
from .models.store import CameraParams
from .models.JumpTo import Model as JumpToMessage
from .models.actions.camera.paramsChanged import Model as ParamsChangedMessage
from .window import Window


@dataclass
class Camera:
    '''
    This class represents the camera of the viewer.
    An instance of this class can be obtained by :attr:`hscmap.window.Window.camera`.
    '''

    _w: Window

    def jump_to(
        self,
        ra: float,
        dec: float,
        *,
        fov: Optional[float] = None,
        duration=0.2,
        non_block=False,
        easing: Optional[Literal['fastStart2', 'fastStart4', 'linear', 'slowStart2', 'slowStart4', 'slowStartStop2', 'slowStartStop4']] = None,
    ) -> None:
        '''
        Jump to the specified position.

        :param ra: Right ascension. The unit is specified at the constructor of the :class:`hscmap.window.Window`.
        :param dec: Declination.
        :param fov: Field of view.
        :param duration: Duration of the jump. The unit is seconds.
        :param non_block: If True, the function returns immediately after the jump command is sent.
        :param easing: Easing function of the jump.

        ::

            m31_position = (10.68470833, 41.26916667)
            window.jump_to(*m31_position, fov=2)
        '''
        self._w._post_message(
            JumpToMessage(
                type='JumpTo',
                ra=self._w._angle_input(ra).radian,
                dec=self._w._angle_input(dec).radian,
                fov=self._w._angle_input(fov).radian if fov is not None else None,
                duration=duration,
                easingFunction=easing,  # type: ignore
            )
        )
        if not non_block:  # pragma: no branch
            time.sleep(duration)

    def _sync(self) -> None:
        self._w.sync()

    @property
    def params(self) -> CameraParams:
        '''
        The parameters of the camera.
        '''
        self._sync()
        return self._w._store_state['camera']['params']

    @params.setter
    def params(self, value: CameraParams):
        action = ParamsChangedMessage(
            type='camera/paramsChanged',
            payload=value,
        )
        self._w._dispatch(action)

    @property
    def center(self) -> Tuple[float, float]:
        '''
        The center of the camera.
        You can also set the center by assigning a tuple of (ra, dec).
        Units are specified at the constructor of the :class:`hscmap.window.Window`.
        ::

            window.camera.center = (10.68470833, 41.26916667)
        '''
        self._sync()
        ra, dec = [Angle(a) for a in self._w._store_state['computed']['center']]
        return (
            self._w._angle_output(ra),
            self._w._angle_output(dec),
        )

    @center.setter
    def center(self, value: Tuple[float, float]):
        self.jump_to(*value, fov=self.fov)

    @property
    def fov(self) -> float:
        '''
        The field of view of the camera.
        You can also set the field of view by assigning a float.
        The unit is specified at the constructor of the :class:`hscmap.window.Window`.
        ::

            window.camera.fov = 2
        '''
        fov = Angle(self.params['fovy'])
        return self._w._angle_output(fov)

    @fov.setter
    def fov(self, value: float):
        self.jump_to(*self.center, fov=value)
