from django.shortcuts import render

# Create your views here.

from .models import Welcome

from django.http import JsonResponse


def welcome(request):
    res = Welcome.objects.all().order_by('-order').first()
    img = 'http://127.0.0.1:8000/media/' + str(res.img)
    return JsonResponse({'code': 100, 'msg': "成功", 'result': img})


# 轮播图接口
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from .models import Banner, Notice
from .serializer import BannerSerializer, NoticeSerializer, CollectionSerializer, CollectionSaveSerializer


class BannerView(GenericViewSet, ListModelMixin):
    queryset = Banner.objects.all().filter(is_delete=False).order_by('order')[:3]
    serializer_class = BannerSerializer

    def list(self, request, *args, **kwargs):
        res = super().list(request, *args, **kwargs)
        notice = Notice.objects.all().order_by('create_time').first()
        serializer = NoticeSerializer(instance=notice)
        return Response({'code': 100, 'msg': '成功', 'banner': res.data, 'notice': serializer.data})


from .models import Collection
from datetime import datetime
from rest_framework.mixins import DestroyModelMixin


# 信息采集接口--查询-登录用户当天采集的所有数据
class CollectionView(GenericViewSet, ListModelMixin, DestroyModelMixin, CreateModelMixin):
    queryset = Collection.objects.all().filter(create_time__gte=datetime.now().date())
    serializer_class = CollectionSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return CollectionSaveSerializer
        else:
            return CollectionSerializer

    def list(self, request, *args, **kwargs):
        res = super().list(request, *args, **kwargs)
        today_count = len(self.get_queryset())
        return Response({'code': 100, 'msg': '成功', 'result': res.data, 'today_count': today_count})

    def destroy(self, request, *args, **kwargs):
        from libs.baidu_ai import BaiDuFace
        instance = self.get_object()
        baidu = BaiDuFace()
        res = baidu.delete_user(instance.name_pinyin, face_token=instance.face_token)
        print(res)
        self.perform_destroy(instance)
        return Response()


# 查询当前用户负责的网格
from .models import Area
from .serializer import AreaSerializer


class AreaView(GenericViewSet, ListModelMixin):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer


from .models import Collection
from django.db.models import Count
from django.db.models.functions import Trunc
from .serializer import StatisticsListSerializer


##统计每天采集人数接口
class StatisticsView(GenericViewSet, ListModelMixin):
    queryset = Collection.objects.annotate(date=Trunc('create_time', 'day')).values('date').annotate(
        count=Count('id')).values('date', 'count')
    serializer_class = StatisticsListSerializer


from libs.baidu_ai import BaiDuFace


# 人脸检测接口 post请求
class FaceView(GenericViewSet):
    def create(self, request, *args, **kwargs):
        # 1 取出前端传入的人脸照片
        avatar_object = request.data.get('avatar')
        if not avatar_object:
            return Response({'code': 103, 'msg': '请正常提交人脸'})
        # 使用百度
        ai = BaiDuFace()
        res = ai.search_user(avatar_object)
        if res.get("error_code") == 0:
            # 查到了，取出userid-->能匹配多个，取第一条
            user_id = res.get('result').get('user_list')[0].get('user_id')
            score = int(res.get('result').get('user_list')[0].get('score'))
            # 根据采集库内查出用户详情
            user = Collection.objects.filter(name_pinyin=user_id).first()
            return Response({'code': 100, 'msg': '匹配成功', 'name': user.name, 'score': score})
        else:
            return Response({'code': 101, 'msg': '匹配失败'})
