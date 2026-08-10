---
title: Spring基础
categories: '技术'
tags: ['Spring']
date: 2025-03-16 20:40:26
cover: cover.png
---

这是一份 Spring 学习笔记，从 IoC、AOP 到 Spring MVC、Spring Boot 再到 SSM 整合，入门需要的内容基本都覆盖了。代码可以直接抄，注释都写在旁边了，有疑问欢迎评论区交流。

## 概述

1. 官网：https://spring.io/（文档：https://spring.io/projects/spring-framework#learn）
2. Spring框架：让 Java EE 开发快起来的框架。
3. Spring体系结构：

![spring-overview](spring-overview.png)

4. **I**nversion **o**f **C**ontrol（控制反转）：把"谁来创建对象"这件事交给框架，具体包含依赖注入（Dependency Injection）和依赖查找（Dependency Lookup）。简单说，对象不再自己 new 自己，而是等框架送上门。

   ![container magic](container-magic.png)

   应用对象与配置数据一结合，`ApplicationContext` 一创建，一个完整可运行的系统就绪了——框架把活都干完了。

5. Bean：可重用的组件。被 IoC 容器管起来的对象都叫 Bean，常见属性有 Class、Name、Scope 等。

6. **A**spect **O**riented **P**rogramming（面向切面编程）：把重复代码抽出来，需要时用动态代理"插"回去——不改源码，照样给已有方法增强。日志、事务这类横切逻辑是它的主场。

## 安装

装依赖有两种姿势：要么手动把 [jar 包](https://repo.spring.io/ui/native/libs-release-local/org/springframework/spring) 扔进 classpath，要么用 Maven 在 `pom.xml` 里声明。现在基本都用后者，下面按功能分类列一下常用依赖：

IoC：

```xml
<!-- spring-context 提供IoC核心容器 -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-context -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-context</artifactId>
    <version>5.2.9.RELEASE</version>
</dependency>
```

AOP：

```xml
<!-- aspectjweaver 提供AOP编程 -->
<!-- https://mvnrepository.com/artifact/org.aspectj/aspectjweaver -->
<dependency>
    <groupId>org.aspectj</groupId>
    <artifactId>aspectjweaver</artifactId>
    <version>1.9.6</version>
    <scope>runtime</scope>
</dependency>
```

事务控制：

```xml
<!-- Spring-tx 提供事务控制 -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-tx -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-tx</artifactId>
    <version>5.2.18.RELEASE</version>
</dependency>
```

SpringMVC：

```xml
<!-- spring-mvc -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-webmvc -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-webmvc</artifactId>
    <version>5.0.2.RELEASE</version>
</dependency>
```

整合JUnit：

```xml
<!-- spring-test 用于整合JUnit -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-test -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-test</artifactId>
    <version>5.2.18.RELEASE</version>
    <scope>test</scope>
</dependency>
```

## Spring配置

### XML配置

早期 Spring 全靠 XML 配置文件撑场面，现在注解虽然成了主流，但 XML 还是经常见到——老项目里、面试题里都是它。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.springframework.org/schema/beans
                        https://www.springframework.org/schema/beans/spring-beans.xsd">
    <!-- bean definitions go here -->
</beans>
```

* 常用XML配置文件头部：

`applicationContext.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:context="http://www.springframework.org/schema/context"
       xmlns:aop="http://www.springframework.org/schema/aop"
       xmlns:tx="http://www.springframework.org/schema/tx"
       xmlns:mvc="http://www.springframework.org/schema/mvc"
       xsi:schemaLocation="http://www.springframework.org/schema/beans
                           https://www.springframework.org/schema/beans/spring-beans.xsd
                           http://www.springframework.org/schema/context
                           https://www.springframework.org/schema/context/spring-context.xsd
                           http://www.springframework.org/schema/tx
                           http://www.springframework.org/schema/tx/spring-tx.xsd
                           http://www.springframework.org/schema/mvc
                           http://www.springframework.org/schema/mvc/spring-mvc.xsd
">

    <!-- bean definitions go here -->

</beans>
```

`springmvc-config.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:context="http://www.springframework.org/schema/context"
       xmlns:mvc="http://www.springframework.org/schema/mvc"
       xsi:schemaLocation="http://www.springframework.org/schema/beans
                           https://www.springframework.org/schema/beans/spring-beans.xsd
                           http://www.springframework.org/schema/context
                           https://www.springframework.org/schema/context/spring-context.xsd
                           http://www.springframework.org/schema/mvc
                           http://www.springframework.org/schema/mvc/spring-mvc.xsd
">

    <!-- bean definitions go here -->

</beans>
```

* context

```xml
<!-- 开启注解扫描包 -->
<context:component-scan base-package="com.lee" >
    <!-- 配置对某些注解不扫描 -->
    <context:exclude-filter type="annotation" expression="org.springframework.stereotype.Controller"/>
    <!-- 配置只对某些注解扫描
    <context:include-filter type="annotation" expression="org.springframework.stereotype.Controller"/>
    -->
</context:component-scan>
```

```xml
<!-- 开启注解配置Bean -->
<context:annotation-config/>
```

* aop

```xml
<!-- 开启注解配置AOP -->
<aop:aspectj-autoproxy/>
```

* mvc：

```xml
<!-- 开启注解配置MVC -->
<mvc:annotation-driven/>
```

* tx：

```xml
<!-- 开启事务注解扫描 -->
<tx:annotation-driven transaction-manager="transactionManager"/>
```

### 常用注解

配置类：

```java
@Configuration
@ComponentScan(basePackages = "org.example")
public class AppConfig  {
    // ...
}
```

* `@Configuration`：指定当前类是一个配置类
  * 属性：`proxyBeanMethods`用于指定代理Bean的方法
  * 配置类组件无依赖关系使用Full模式（`proxyBeanMethods=true`，默认），配置类组件有依赖关系使用Lite模式（`proxyBeanMethods=false`）
* `@ComponentScan`：指定配置类创建容器需扫描的包
  * 属性：`value`用于指定创建容器需扫描的包名
* `@EnableAspectJAutoProxy`：指定配置类开启注解配置AOP
* `@Bean`：指定（配置类中）当前方法的返回值为bean对象存入容器中
  * 属性：`name`用于指定bean的id，默认值为当前方法的名称
  * 若方法有参数，则Spring会按照类型（必要时依据变量名）注入bean对象

导入类：

* **`@Import`**：指定当前类导入组件（这些类会被创建并放入Spring容器中）
  * 属性：`value`用于指定导入组件的字节码
* `@ImportResource`：指定当前类导入某一资源文件（如Spring的`applicationContext.xml`）
  * 属性：`value`用于指定资源文件的名称
* `@PropertySource`：指定当前类导入properties文件的位置及名称（可使用`@Value`注解以及`SpEL`导入数据）
  * 属性：`value`用于指定properties文件的位置及名称

条件注解：

* `@ConditionalOnProperty`：指定当前类当配置文件中有对应属性和值时才被初始化
* `@ConditionalOnClass`：指定当前类当环境中有字节码时才被初始化
* `@ConditionalOnMissingBean`：指定当前类当环境中没有对应Bean时才被初始化



##  IoC

IoC 容器有两个主要实现类，记住区别就行：`ApplicationContext` 一创建就把对象全部造好（立即加载），`BeanFactory` 要等用到的时候才造（延迟加载）。

* `ApplicationContext`
  * `ClassPathXmlApplicationContext`加载类路径下配置文件创建容器
  * `FileSystemApplicationContext`加载磁盘路径下配置文件创建容器
  * `AnnotationConfigApplicationContext`读取注解以及配置类创建容器

```java
// create and configure beans
ApplicationContext context = new ClassPathXmlApplicationContext("services.xml", "daos.xml");

// retrieve configured instance
PetStoreService service = context.getBean("petStore", PetStoreService.class);

// use configured instance
List<String> userList = service.getUsernameList();
```

`ApplicationContext`构建核心容器时创建对象采用立即加载（读取完配置文件时创建）的方式

* `BeanFactory`

```java
DefaultListableBeanFactory factory = new DefaultListableBeanFactory();
// populate the factory with bean definitions

// now register any needed BeanPostProcessor instances
factory.addBeanPostProcessor(new AutowiredAnnotationBeanPostProcessor());
factory.addBeanPostProcessor(new MyBeanPostProcessor());

// now start using the factory
```

`BeanFactory`构建核心容器时创建对象采用延迟加载（根据id获取对象时创建）的方式

### 创建对象

#### XML

* 构造函数实例化

```xml
<bean id="exampleBean" class="examples.ExampleBean"/>

<bean name="anotherExample" class="examples.ExampleBeanTwo"/>
```

对应Java类：

```java
public class ExampleBean {
    public ExampleBean() {
    }
}
```

```java
public class ExampleBeanTwo {
    public ExampleBeanTwo() {
    }
}
```

* 工厂普通方法实例化

```xml
<!-- the factory bean, which contains a method called createInstance() -->
<bean id="serviceLocator" class="examples.DefaultServiceLocator">
    <!-- inject any dependencies required by this locator bean -->
</bean>

<!-- the bean to be created via the factory bean -->
<bean id="clientService"
    factory-bean="serviceLocator"
    factory-method="createClientServiceInstance"/>

<bean id="accountService"
    factory-bean="serviceLocator"
    factory-method="createAccountServiceInstance"/>
```

对应Java类：

```java
public class DefaultServiceLocator {

    private static ClientService clientService = new ClientServiceImpl();

    private static AccountService accountService = new AccountServiceImpl();

    public ClientService createClientServiceInstance() {
        return clientService;
    }

    public AccountService createAccountServiceInstance() {
        return accountService;
    }
}
```

* 工厂静态方法实例化

```xml
<bean id="clientService"
    class="examples.ClientService"
    factory-method="createInstance"/>
```

对应Java类：

```java
public class ClientService {
    private static ClientService clientService = new ClientService();
    private ClientService() {}

    public static ClientService createInstance() {
        return clientService;
    }
}
```

#### 注解

* `@Component`：指定其他层类为bean对象存入容器中
  * 属性：`value`用于指定bean的id，默认值为当前类类名（首字母小写）
* `@Controller`：指定表现层类为bean对象存入容器中
  * 属性：`value`用于指定bean的id，默认值为当前类类名（首字母小写）
* `@Service`：指定业务层类为bean对象存入容器中
  * 属性：`value`用于指定bean的id，默认值为当前类类名（首字母小写）
* `@Repository`：指定持久层类为bean对象存入容器中
  * 属性：`value`用于指定bean的id，默认值为当前类类名（首字母小写）

### 依赖注入

#### XML

* 构造函数依赖注入（构造函数+`constructor-arg`标签）

```xml
<bean id="exampleBean" class="examples.ExampleBean">
    <!-- constructor injection using the nested ref element -->
    <constructor-arg>
        <ref bean="anotherExampleBean"/>
    </constructor-arg>

    <!-- constructor injection using the neater ref attribute -->
    <constructor-arg ref="yetAnotherBean"/>

    <constructor-arg type="int" value="1"/>
</bean>

<bean id="anotherExampleBean" class="examples.AnotherBean"/>
<bean id="yetAnotherBean" class="examples.YetAnotherBean"/>
```

对应Java类：

```java
public class ExampleBean {

    private AnotherBean beanOne;

    private YetAnotherBean beanTwo;

    private int i;

    public ExampleBean(AnotherBean anotherBean, YetAnotherBean yetAnotherBean, int i) {
        this.beanOne = anotherBean;
        this.beanTwo = yetAnotherBean;
        this.i = i;
    }
}
```

`<constructor-arg>`标签中的属性：

| 属性    | 描述                                                 |
| :------ | :--------------------------------------------------- |
| `type`  | 指定注入的数据（构造函数参数）类型                   |
| `index` | 指定注入的数据（构造函数参数）索引，索引从0开始      |
| `name`  | 指定注入的数据（构造函数参数）名称                   |
| `value` | 指定注入数据的值，值类型为基本数据类型或`String`类型 |
| `ref`   | 指定注入数据引用，值类型为其他Bean类型               |

* Set方法依赖注入（set方法+`property`标签）

```xml
<bean id="exampleBean" class="examples.ExampleBean">
    <!-- setter injection using the nested ref element -->
    <property name="beanOne">
        <ref bean="anotherExampleBean"/>
    </property>

    <!-- setter injection using the neater ref attribute -->
    <property name="beanTwo" ref="yetAnotherBean"/>
    <property name="integerProperty" value="1"/>
</bean>

<bean id="anotherExampleBean" class="examples.AnotherBean"/>
<bean id="yetAnotherBean" class="examples.YetAnotherBean"/>
```

对应Java类：

```java
public class ExampleBean {

    private AnotherBean beanOne;

    private YetAnotherBean beanTwo;

    private int i;

    public void setBeanOne(AnotherBean beanOne) {
        this.beanOne = beanOne;
    }

    public void setBeanTwo(YetAnotherBean beanTwo) {
        this.beanTwo = beanTwo;
    }

    public void setIntegerProperty(int i) {
        this.i = i;
    }
}
```

`<property>`标签中的属性：

| 属性    | 描述                                                         |
| :------ | :----------------------------------------------------------- |
| `name`  | 指定注入的数据（set方法名(`setBeanOne`)中的参数名(`beanOne`)）名称 |
| `value` | 指定注入数据的值，值类型为基本数据类型或`String`类型         |
| `ref`   | 指定注入数据引用，值类型为其他Bean类型                       |

`<property>`标签中的子标签：

| 属性    | 描述                                             |
| :------ | :----------------------------------------------- |
| `array` | 指定注入数据为数组类型，使用`value`或`ref`插入值 |
| `list`  | 指定注入数据为列表类型，使用`value`或`ref`插入值 |
| `set`   | 指定注入数据为集合类型，使用`value`或`ref`插入值 |
| `map`   | 指定注入数据为映射类型，使用`entry`插入值        |
| `props` | 指定注入数据为属性类型，使用`props`插入值        |

```xml
<!-- 注入集合类型数据（只能通过XML方式实现） -->
<bean id="moreComplexObject" class="example.ComplexObject">
    <!-- results in a setAdminEmails(java.util.Properties) call -->
    <property name="adminEmails"> <!-- Map结构数据注入可用<map>, <props>标签 -->
        <props>
            <prop key="administrator">administrator@example.org</prop>
            <prop key="support">support@example.org</prop>
            <prop key="development">development@example.org</prop>
        </props>
    </property>
    <!-- results in a setSomeList(java.util.List) call -->
    <property name="someList"> <!-- List结构数据注入可用<list>, <set>, <array>标签 -->
        <list>
            <value>a list element followed by a reference</value>
            <ref bean="myDataSource" />
        </list>
    </property>
    <!-- results in a setSomeMap(java.util.Map) call -->
    <property name="someMap">
        <map>
            <entry key="an entry" value="just some string"/>
            <entry key ="a ref" value-ref="myDataSource"/>
        </map>
    </property>
    <!-- results in a setSomeSet(java.util.Set) call -->
    <property name="someSet">
        <set>
            <value>just some string</value>
            <ref bean="myDataSource" />
        </set>
    </property>
</bean>
```

#### 注解

* `@Autowired`：指定注入数据的变量或方法，按照类型（必要时依据变量名）注入bean对象（容器只要有唯一bean对象与之匹配）
  * 若有0个对应bean对象则报错，若有2个或以上对应bean对象则按变量名进行匹配，若无一致变量名则报错。
* `@Qualifier`：指定注入数据的变量或方法，按照名称（bean的id）注入bean对象（对类成员注入时需配合`@Autowired`一起使用）
  * 属性：`value`用于指定注入bean的`id`
* `@Resource`：指定注入数据的变量或方法，按照名称（bean的id）注入bean对象
  * 属性：`name`用于指定注入bean的`id`
* `@Value`：指定注入数据的变量或方法，按照数据值注入基本数据类型或`String`类型
  * 属性：`value`用于指定注入bean的值（可使用`SpEL`）

### 作用范围

#### XML

* 设置`<bean>`标签中的`scope`属性即可指定对象作用域。

| 作用域      | 描述                                                         |
| :---------- | :----------------------------------------------------------- |
| singleton   | (Default) Scopes a single bean definition to a single object instance for each Spring IoC container. |
| prototype   | Scopes a single bean definition to any number of object instances. |
| request     | Scopes a single bean definition to the lifecycle of a single HTTP request. That is, each HTTP request has its own instance of a bean created off the back of a single bean definition. Only valid in the context of a web-aware Spring `ApplicationContext`. |
| session     | Scopes a single bean definition to the lifecycle of an HTTP `Session`. Only valid in the context of a web-aware Spring `ApplicationContext`. |
| application | Scopes a single bean definition to the lifecycle of a `ServletContext`. Only valid in the context of a web-aware Spring `ApplicationContext`. |
| websocket   | Scopes a single bean definition to the lifecycle of a `WebSocket`. Only valid in the context of a web-aware Spring `ApplicationContext`. |

#### 注解

* `@Scope`：指定当前类的作用范围
  * 属性：`value`用于指定bean的作用范围（`singleton`、`prototype`）

### 生命周期

#### XML

* 生命周期

  * `singleton`生命周期：容器创建时出生，容器销毁时死亡

  * `prototype`生命周期：使用对象时出生，无引用且长时间无用被回收死亡

* 初始化方法

```xml
<bean id="exampleInitBean" class="examples.ExampleBean" init-method="init"/>
```

对应Java类：

```java
public class ExampleBean {

    public void init() {
        // do some initialization work
    }
}
```

* 析构化方法

```xml
<bean id="exampleInitBean" class="examples.ExampleBean" destroy-method="cleanup"/>
```

对应Java类：

```java
public class ExampleBean {

    public void cleanup() {
        // do some destruction work (like releasing pooled connections)
    }
}
```

#### 注解

* `@PostConstruct`：指定当前方法为初始化方法
* `@PreDestroy`：指定当前方法为析构化方法

## AOP

AOP 的概念术语不少，初次接触容易晕。先把下面这串名词过一遍，后面声明切面、切点、通知就顺了：

* 概念

  - Aspect：切面，即一个横跨多个核心逻辑的功能，或者称之为系统关注点

  - Joinpoint：连接点，即定义在应用程序流程的何处插入切面的执行

  - Pointcut：切入点，即一组连接点的集合

  - Advice：增强，指特定连接点上执行的动作

  - Introduction：引介，指为一个已有的Java对象动态地增加新的接口

  - Weaving：织入，指将切面整合到程序的执行流程中

  - Interceptor：拦截器，是一种实现增强的方式

  - Target Object：目标对象，即真正执行业务的核心逻辑对象

  - AOP Proxy：AOP代理，是客户端持有的增强后的对象引用


### 声明切面

#### XML

* 使用`aop:aspect`标签声明一个切面类（通知方法类）

```xml
<!-- 配置AOP -->
<aop:config>
    <!-- 声明切面 -->
    <aop:aspect id="myAspect" ref="aBean"> <!-- id指切面id，ref指通知bean -->
        ...
    </aop:aspect>
</aop:config>
```

#### 注解

* `@Aspect`：指定当前类为切面类

```java
package org.xyz;
import org.aspectj.lang.annotation.Aspect;

@Component("myAspect")
@Aspect
public class NotVeryUsefulAspect {

}
```

### 声明切点

#### XML

* 使用`aop:pointcut`标签声明一个切入点（方法）

```xml
<aop:config>

    <aop:pointcut id="businessService" expression="execution(* com.xyz.myapp.service.*.*(..))"/>
    <!-- id指切入点id expression指切入表达式内容-->

</aop:config>
```

* 切入表达式

完整写法：`execution(modifier type package.class.method(argType))`

方法简写：`execution(* package.*.*(..))`

1. `modifier`可省略
2. `type`可用`*`表示任意返回值
3. `package`可用`*`表示任意一个包，可用`..`表示任意一个包及其子包，不推荐
4. `class`可用`*`表示任意一个类
5. `method`可用`*`表示任意一个方法
6. `argType`可用`*`表示任意一个参数（>=1），可用`..`表示任意个参数（>=0）

#### 注解

* `@Pointcut`：指定当前方法为切入点（方法）`id`
  * `value`用于指定切入表达式

```java
@Pointcut("execution(* transfer(..))") // the pointcut expression
private void anyOldTransfer() {} // the pointcut signature
```

### 声明通知

#### XML

* 使用`aop:before`声明前置通知，在切入点执行之前执行

```xml
<aop:aspect id="beforeExample" ref="aBean">

    <aop:before pointcut="execution(* com.xyz.myapp.dao.*.*(..))" method="doAccessCheck"/>
    <!-- pointcut指切入点 method指前置通知方法 -->
    ...
</aop:aspect>
```

```xml
<aop:aspect id="beforeExample" ref="aBean">

    <aop:before pointcut-ref="dataAccessOperation" method="doAccessCheck"/>
    <!-- pointcut-ref指切入点id method指前置通知方法 -->
    ...
</aop:aspect>
```

* 使用`aop:after-returning`声明后置通知，在切入点正常执行之后执行

```xml
<aop:aspect id="afterReturningExample" ref="aBean">

    <aop:after-returning pointcut-ref="dataAccessOperation" method="doAccessCheck"/>
    ...
</aop:aspect>
```

* 使用`aop:after-throwing`声明异常通知，在切入点产生异常之后执行

```xml
<aop:aspect id="afterThrowingExample" ref="aBean">

    <aop:after-throwing pointcut-ref="dataAccessOperation" method="doRecoveryActions"/>
    ...
</aop:aspect>
```

* 使用`aop:after`声明最终通知，在切入点执行之后执行

```xml
<aop:aspect id="afterFinallyExample" ref="aBean">

    <aop:after pointcut-ref="dataAccessOperation" method="doReleaseLock"/>
    ...
</aop:aspect>
```

* 使用`aop:around`声明环绕通知，切入点需显式调用执行

```xml
<aop:aspect id="aroundExample" ref="aBean">

    <aop:around pointcut-ref="businessService" method="doBasicProfiling"/>
    ...
</aop:aspect>
```

```java
public Object doBasicProfiling(ProceedingJoinPoint pjp) {
    Object rtValue = null;
    try {
        Object[] args = pjp.getArgs(); // 得到方法执行所需参数
        System.out.println("前置通知方法");
        rtValue = pjp.proceed(); // 明确调用业务层方法
        System.out.println("后置通知方法");
        return rtValue;
    } catch (Throwable throwable) {
        System.out.println("异常通知方法");
        throw new RuntimeException(throwable);
    } finally {
        System.out.println("最终通知方法");
    }
}
```

#### 注解

* `@Before`：指定当前方法为前置通知方法
  * `value`用于指定切入点或切入点`id`（需添加`()`）
* `@AfterReturning`：指定当前方法为后置通知方法
  * `value`用于指定切入点或切入点`id`（需添加`()`）
* `@AfterThrowing`：指定当前方法为异常通知方法
  * `value`用于指定切入点或切入点`id`（需添加`()`）
* `@After`：指定当前方法为最终通知方法
  * `value`用于指定切入点或切入点`id`（需添加`()`）
* `@Around`：指定当前方法为环绕通知方法
  * `value`用于指定切入点或切入点`id`（需添加`()`）

### 事务控制

#### XML

1. 配置事务管理器

```xml
<!-- 配置Spring事务管理器 -->
<bean id="transactionManager" class="org.springframework.jdbc.datasource.DataSourceTransactionManager">
    <!-- 原理:控制数据源 -->
    <property name="dataSource" ref="dataSource"/>
</bean>
```

2. 配置事务通知

```xml
<!-- 配置事务通知 -->
<tx:advice id="txAdvice" transaction-manager="transactionManager">
    <!-- 配置事务的属性 -->
    <tx:attributes>
        <!-- REQUIRED指定当前方法必需在事务环境中运行(默认值), 如果当前有事务环境就加入, 否则就新建一个事务 -->
        <tx:method name="*" propagation="REQUIRED" read-only="false"/>
        <!-- SUPPORTS指定当前方法加入当前事务环境, 如果当前没有事务, 就以非事务方式执行 -->
        <tx:method name="select*" propagation="SUPPORTS" read-only="true"/>
    </tx:attributes>
</tx:advice>
```

3. 配置AOP

```xml
<!-- 配置AOP -->
<aop:config>
    <!-- 配置切入点表达式 -->
    <aop:pointcut id="pt1" expression="execution(* com.lee.service.impl.*.*(..))"/>
    <!-- 建立切入点表达式与事务通知关系 -->
    <aop:advisor advice-ref="txAdvice" pointcut-ref="pt1"/>
</aop:config>
```

#### 注解

* `@Transactional`：指定当前类中所有public方法都具有该类型的事务属性或指定当前方法具有该类型的事务属性

1. 配置事务管理器

```xml
<!-- 配置Spring事务管理器 -->
<bean id="transactionManager" class="org.springframework.jdbc.datasource.DataSourceTransactionManager">
    <!-- 原理:控制数据源 -->
    <property name="dataSource" ref="dataSource"/>
</bean>
```

2. 指定类或指定方法添加`@Transactional`注解

```java
@Service
@Transactional
public class AdminServiceImpl implements AdminService {
    ...
}
```

3. 开启事务注解扫描

```xml
<!-- 开启事务注解扫描 -->
<tx:annotation-driven transaction-manager="transactionManager"/>
```

## Spring MVC

Spring MVC 是 Web 层的 MVC 框架。先认识它的几个核心组件，再看请求是怎么流转的：

* 组件：

  * `DispatcherServlet`：前端控制器，MVC控制流程核心

  * `HandlerMapping`：处理器映射器，根据用户请求找到Handler

  * `Handler`：处理器，对具体的用户请求进行响应

  * `HandlerAdapter`：处理器适配器，对Handler进行执行

  * `ViewResolver`：视图解析器，根据结果生产View视图
  * `View`：视图

* 使用Spring MVC时，整个Web应用程序按如下顺序启动：

  1. 启动Tomcat服务器
  2. Tomcat读取web.xml并初始化DispatcherServlet
  3. DispatcherServlet创建IoC容器并自动注册到ServletContext中

  启动后，浏览器发出的HTTP请求全部由DispatcherServlet接收，并根据配置转发到指定Controller的指定方法处理。

* 执行流程

![SpringMVC执行流程](SpringMVC执行流程.png)

### 常用组件

#### 前端控制器

* `DispatcherServlet`：前端控制器（管理控制器对象），配置于`web.xml`

```xml
<!-- 启动Spring MVC: 部署DispatcherServlet -->
<servlet>
    <!-- 配置Spring MVC的前端核心控制器 -->
    <servlet-name>dispatcherServlet</servlet-name>
    <servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>
    <!-- 加载Spring MVC配置文件 -->
    <init-param>
        <param-name>contextConfigLocation</param-name>
        <param-value>classpath:spring_conf/springmvc-config.xml</param-value>
    </init-param>
    <!-- 服务器启动后立即加载Spring MVC配置文件 -->
    <load-on-startup>1</load-on-startup>
</servlet>
<servlet-mapping>
    <servlet-name>dispatcherServlet</servlet-name>
    <url-pattern>/</url-pattern>
</servlet-mapping>
```

#### 编码过滤器

* `CharacterEncodingFilter`：编码过滤器，配置于`web.xml`中

```xml
<!-- 配置字符编码过滤器 -->
<filter>
    <filter-name>characterEncodingFilter</filter-name>
    <filter-class>org.springframework.web.filter.CharacterEncodingFilter</filter-class>
    <init-param>
        <param-name>encoding</param-name>
        <param-value>utf-8</param-value>
    </init-param>
</filter>
<filter-mapping>
    <filter-name>characterEncodingFilter</filter-name>
    <url-pattern>/*</url-pattern>
</filter-mapping>
```

#### 视图解析器

* `InternalResourceViewResolver`：（内部资源）视图解析器，配置于`springmvc-config.xml`

```xml
<!-- 配置内部资源视图解析器 -->
<bean id="internalResourceViewResolver" class="org.springframework.web.servlet.view.InternalResourceViewResolver">
    <!-- 前缀 -->
    <property name="prefix" value="/WEB-INF/view/"/>
    <!-- 后缀 -->
    <property name="suffix" value=".jsp"/>
</bean>
```

#### 文件解析器

* `CommonsMultipartResolver`：文件解析器，配置于`springmvc-config.xml`中

```xml
<!-- 配置文件解析器 -->
<bean id="multipartResolver" class="org.springframework.web.multipart.commons.CommonsMultipartResolver">
    <!-- 配置文件上传的最大限值 -->
    <property name="maxUploadSize" value="10485760" /> <!-- 单位为Byte -->
</bean>
```

文件上传方法：

```java
@RequestMapping("/fileUpload")
public String fileUpload(HttpServletRequest request, MultipartFile upload) throws IOException { //多文件上传时使用MultipartFile[] uploads
    // 设置上传位置
    String destPath = request.getSession().getServletContext().getRealPath("/uploads/");
    File destFile = new File(destPath);
    if(!destFile.exists()) { // 判断路径是否存在
        destFile.mkdirs(); // 创建文件夹
    }

    // 设置文件名称
    String UploadFilename = upload.getOriginalFilename();
    String uuid = UUID.randomUUID().toString().replace("-", "");
    UploadFilename = uuid + "_" + UploadFilename;

    // 开始上传文件
    upload.transferTo(new File(destPath, UploadFilename));
    return "success";
}
```

文件上传三要素：表单项`type="file"`，表单`method="POST"`、`enctype="multipart/form-data"`

```html
<form action="${pageContext.request.contextPath}/fileUpload" method="POST" enctype="multipart/form-data">
    名称: <input type="text" name="picture-name"/><br/>
    文件: <input type="file" name="upload"/><br/>
    <input type="submit" value="提交"/>
</form>
```

#### 类型转换器

* `ConversionServiceFactoryBean`子类：自定义类型转换器，配置于`springmvc-config.xml`中（同时需设置`mvc:annotation-driven`中的`conversion-service`属性使其生效）

```xml
<!-- 配置自定义类型转换器 -->
<bean id="conversionService" class="org.springframework.context.support.ConversionServiceFactoryBean">
    <property name="converters">
        <set>
            <!-- 类型转换器集合中添加了StringToDateConverter -->
            <bean class="com.lee.utils.StringToDateConverter"></bean>
        </set>
    </property>
</bean>
```

类型转换类实现`org.springframework.core.convert.converter.Converter<S,T>`接口：

```java
package com.lee.utils;

import org.springframework.core.convert.converter.Converter;

import java.text.DateFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;

public class StringToDateConverter implements Converter<String, Date> {
    /**
     * 将"yyyy-MM-dd"格式字符串转化为日期
     * @param s
     * @return
     */
    @Override
    public Date convert(String s) {
        // 判断
        if (s == null) {
            throw new RuntimeException("请输入合法日期数据");
        }
        try {
            DateFormat df = new SimpleDateFormat("yyyy-MM-dd");
            return df.parse(s);
        } catch (ParseException e) {
            throw new RuntimeException("日期格式非法");
        }
    }
}
```

`springmvc-config.xml`：

```xml
<!-- 让conversionService生效 -->
<mvc:annotation-driven conversion-service="conversionService" />
```

#### 异常处理器

* `SimpleMappingExceptionResolver`：简单异常处理器，配置于`springmvc-config.xml`中

```xml
<!-- 配置异常处理器 -->
<bean id="exceptionResolver" class="org.springframework.web.servlet.handler.SimpleMappingExceptionResolver">
    <!-- 默认错误视图 -->
    <property name="defaultErrorView" value="general-error"/> <!-- value指定错误视图 -->
    <!-- 匹配异常视图 -->
    <property name="exceptionMappings">
        <map>
            <entry key="com.lee.exception.MyException" value="my-error"/>
        </map>
    </property>
</bean>
```

* `HandlerExceptionResolver`子类：自定义异常处理器，配置于`springmvc-config.xml`中

```xml
<!-- 配置异常处理器 -->
<bean id="systemExceptionResolver" class="com.lee.exception.SystemExceptionResolver"></bean>
```

自定义异常处理器实现`org.springframework.web.servlet.HandlerExceptionResolver`接口：

```java
package com.lee.exception;

import org.springframework.web.servlet.HandlerExceptionResolver;
import org.springframework.web.servlet.ModelAndView;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class SystemExceptionResolver implements HandlerExceptionResolver {
    /**
     * 处理异常
     * @param httpServletRequest
     * @param httpServletResponse
     * @param o
     * @param e
     * @return
     */
    @Override
    public ModelAndView resolveException(HttpServletRequest httpServletRequest, HttpServletResponse httpServletResponse, Object o, Exception e) {
        // 获取异常对象
        SystemException exception = null;
        if (e instanceof SystemException) {
            exception = (SystemException) e;
        } else {
            exception = new SystemException("系统出错了...");
        }
        // 跳转至错误页面
        ModelAndView mv = new ModelAndView();
        mv.addObject("errorMessage", exception.getMessage());
        mv.setViewName("error");
        return mv;
    }
}
```

#### 资源阻拦器

* `mvc:resources`：（静态）资源阻拦器，配置于`springmvc-config.xml`中

```xml
<!-- 过滤静态资源 -->
<mvc:resources mapping="/css/**" location="/css/"/>
<mvc:resources mapping="/images/**" location="/images/"/>
<mvc:resources mapping="/js/**" location="/js/"/>
<mvc:resources mapping="/fonts/**" location="/fonts/"/>
```

* `mvc:default-servlet-handler`：处理静态资源，配置于`springmvc-config.xml`中

```xml
<!-- 处理静态资源 -->
<mvc:default-servlet-handler/>
```

#### 方法拦截器

* `mvc:interceptors`：（控制器）方法拦截器，配置于`springmvc-config.xml`中

```xml
<!-- 配置拦截器 -->
<mvc:interceptors>
    <!-- 配置单个拦截器 -->
    <mvc:interceptor>
        <!-- 拦截的路径 -->
        <mvc:mapping path="/**"/>
        <!-- 不拦截的路径 -->
        <mvc:exclude-mapping path="static/bootstrap/**"/>
        <mvc:exclude-mapping path="static/my-ui/**"/>
        <mvc:exclude-mapping path="system/login"/>
        <mvc:exclude-mapping path="system/getVerifiedCodeImage"/>
        <!-- 配置拦截类 -->
        <bean class="com.lee.interceptor.LoginInterceptor"/>
    </mvc:interceptor>
</mvc:interceptors>
```

控制拦截器类实现`org.springframework.web.servlet.HandlerInterceptor`接口：

```java
package com.lee.interceptor;

import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.ModelAndView;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 * 用户登录拦截器
 */
public class LoginInterceptor implements HandlerInterceptor {
    /**
     * 该方法会在控制器方法前执行,其返回值表示是否中断后续操作
     * @param request
     * @param response
     * @param handler
     * @return
     * @throws Exception
     */
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 获取请求的url
        String url = request.getRequestURI();
        // 判断用户是否已登录
        if (request.getSession().getAttribute("userInfo") != null) {
            return true;
        }
        // 用户未登录,拦击其请求并将其转发到用户登录页面
        request.getRequestDispatcher("/WEB-INF/view/system/login.jsp").forward(request, response);
        return false;
    }

    /**
     * 该方法会在控制器方法调用之后,且解析视图之前调用
     * @param request
     * @param response
     * @param handler
     * @param modelAndView
     * @throws Exception
     */
    @Override
    public void postHandle(HttpServletRequest request, HttpServletResponse response, Object handler, ModelAndView modelAndView) throws Exception {

    }

    /**
     * 该方法会在整个请求完成,既视图渲染结束之后执行
     * @param request
     * @param response
     * @param handler
     * @param ex
     * @throws Exception
     */
    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) throws Exception {

    }
}
```

### 获取数据

#### 获取参数

* 可通过参数列表获取基本数据类型或`String`类型

控制器方法参数：

```java
@RequestMapping("/method")
public String method(String username) {...} // 请求参数名为username
```

`form`表单：

```html
<input type="text" name="username" />
```

* 可通过参数列表获取封装后bean类型

控制器方法参数：

```java
@RequestMapping("/method")
public String method(Account account) {...} // 请求参数可被封装为Account
```

`form`表单：

```html
<form action="method" method="post">
    姓名: <input type="text" name="username" /><br/>
    密码: <input type="password" name="password"><br/>
    金额: <input type="text" name="money"><br/>
    <input type="submit" value="提交"/>
</form>
```

若`Account`类中含有引用类型，则`form`表单`name`属性使用`reference.attributes`。

若`Account`类中含有集合类型，则`form`表单`name`属性使用`list[0]`、`map['key']`。

* 可通过参数列表获取字符数组

```java
@RequestMapping("/method")
public String method(String[] strs) {...} // 有多个请求参数名为strs
```

#### 获取`Model`对象

* 可通过参数列表直接获取`Model`、`ModelAndView`、`HttpServletRequest`、`HttpServletResponse`、`HttpSession`

```java
@RequestMapping("/testModel")
public String testModel(Model model) { ... }
```

#### 获取数据

* 获取请求体（使用`@RequestBody`注解）

```java
@RequestMapping("/testString")
@ResponseBody
public void testString(@RequestBody String str/* 指定当前方法参数从HTTP请求体中获取字符串 */){
    System.out.println(str);
}
```

* 获取对象或集合（使用`@RequestBody`注解）

```java
@RequestMapping("/testJSON")
@ResponseBody
public void testJSON(@RequestBody List<User> userList/* 指定当前方法参数从HTTP请求体中获取集合(JSON会被转换为集合) */){
    System.out.println(userList);
}
```

### 响应数据

#### 返回页面

* 返回至指定页面（根据视图解析器）

```java
@RequestMapping("/testString")
public String testString() {
    ...
    return "success"; // 等价于 forward:<prefix>success<suffix>
}
```

返回字符串为`forward: ...`，可请求转发至指定页面（默认情况）。

返回字符串为`redirect: ...`，可重定向至指定页面（不用添加项目名称）。

返回字符串会与视图解析器的前后缀拼接构成资源地址并跳转。

#### 返回`ModelAndView`对象

* 返回`ModelAndView`对象

```java
@RequestMapping("/testModelAndView")
public ModelAndView testModelAndView() {
    ...
    return mv;
}
```

`public ModelAndView addObject(String attributeName, Object attributeValue) /* 设置模型数据 */`

`public void setViewName(@Nullable String viewName) /* 设置视图名称 */`

使用`ModelAndView`对象可设置视图名称、设置模型数据等。

#### 返回数据

* 返回字符串（使用`@ResponseBody`注解）

```java
@RequestMapping("/testString")
@ResponseBody // 指定当前方法返回字符串至HTTP响应体
public String testString(){
    return "Hello world!";
}
```

* 返回对象或集合（使用`@ResponseBody`注解）

```java
@RequestMapping("/testJSON")
@ResponseBody // 指定当前方法返回对象(对象会被转换为JSON)至HTTP响应体
public User testJSON(){
    User user = new User();
    user.setUsername("张三");
    user.setAddress("天津");
    return user;
}
```

### Rest风格

* Restful制作表现层接口
  * 新增：POST
  * 删除：DELETE
  * 修改：PUT
  * 查询：GET
* 接收参数：
  * 实体数据：`@RequestBody`
  * 路径变量：`@PathVarible`
* 实例

`com.lee.controller.BookController`：

```java
package com.lee.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.lee.controller.util.Result;
import com.lee.domain.Book;
import com.lee.service.BookService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/books")
public class BookController {
    @Autowired
    private BookService service;

    @GetMapping
    public Result getAll() {
        return new Result(true, service.list());
    }

    @PostMapping
    public Result save(@RequestBody Book book) {
        return new Result(service.save(book));
    }

    @PutMapping
    public Result update(@RequestBody Book book) {
        return new Result(service.updateById(book));
    }

    @DeleteMapping("/{id}")
    public Result delete(@PathVariable Integer id) {
        return new Result(service.removeById(id));
    }

    @GetMapping("/{id}")
    public Result getById(@PathVariable Integer id) {
        return new Result(true, service.getById(id));
    }

    @GetMapping("/{currentPage}/{pageSize}")
    public Result getPage(@PathVariable Integer currentPage, @PathVariable Integer pageSize, Book book) {
        System.out.println(book);
        IPage<Book> page = service.getPage(currentPage, pageSize, book);
        // 如果当前页码值大于总页码值则重新查询最后一页
        if (currentPage > page.getPages()) {
            page = service.getPage((int) page.getPages(), pageSize, book);
        }
        return new Result(true, page);
    }
    /**
     * @Override
     * public IPage<Book> getPage(Integer currentPage, Integer pageSize, Book book) {
     *     // 组织条件
     *     LambdaQueryWrapper<Book> lqw = new LambdaQueryWrapper<>();
     *     lqw.like(Strings.isNotEmpty(book.getType()), Book::getType, book.getType());
     *     lqw.like(Strings.isNotEmpty(book.getName()), Book::getName, book.getName());
     *     lqw.like(Strings.isNotEmpty(book.getDescription()), Book::getDescription, book.getDescription());
     *     // 分页查询
     *     IPage page = new Page(currentPage, pageSize);
     *     mapper.selectPage(page, lqw);
     *     return page;
     * }
     */
}
```

`com.lee.controller.util.Result`：设计统一的返回值结果类型便于前端开发读取数据，返回值结果类型类用于后端与前端进行数据格式统一，也称为前后端数据协议

```java
package com.lee.controller.util;

import lombok.Data;

@Data
public class Result {
    private Boolean flag;
    private Object data;
    private String msg;

    public Result() {}

    public Result(Boolean flag) {
        this.flag = flag;
    }

    public Result(Boolean flag, Object data) {
        this.flag = flag;
        this.data = data;
    }

    public Result(Boolean flag, String msg) {
        this.flag = flag;
        this.msg = msg;
    }
}
```

`com.lee.controller.util.ProjectExceptionAdvice`：对异常统一处理，返回指定信息

```java
package com.lee.controller.util;

import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ProjectExceptionAdvice {

    @ExceptionHandler // 拦截所有的异常信息
    public Result doException(Exception ex) {
        // 记录日志
        // 通知运维
        // 通知开发
        ex.printStackTrace();
        return new Result(false, "服务器故障，请稍后再试！");
    }
}
```

### 常用注解

* **`@RequestMapping`**：指定当前方法（处理请求方法）或当前类（处理请求方法类）与请求URL之间的关联
  * 属性：`value`用于指定请求URL的路径，`method`用于指定请求方式，`params`用于指定限制请求参数的条件
  * `method`指定注解：`@GetMapping`、`@PostMapping`、`@PutMapping`、`@DeleteMapping`
  * `params`常用格式：`params={"name"}`表示请求参数必须含有`name`，`params={"money!100"}`表示请求参数`money`不能为100
* **`@ResponseBody`**：指定当前控制器方法返回字符串（控制器方法返回`String`）或对象或集合（控制器方法返回对象或集合，对象或集合会被转换为JSON）至HTTP响应体
* **`@RequestBody`**：指定当前控制器方法参数从HTTP请求体中获取字符串（控制器方法参数为`String`）或对象或集合（控制器方法参数为对象或集合，JSON会被转换为对象或集合）
* **`@PathVarible`**：指定当前控制器方法参数获取URL中的占位符
  * 属性：`value`用于指定URL中的占位符名称
* `@RequestParam`：指定当前控制器方法参数获取指定名称的请求参数值
  * 属性：`value`用于指定请求参数的名称，`required`用于指定参数是否必须传入（默认`true`），`defaultValue`用于指定参数默认值

* `@RequestHeader`：指定当前控制器方法参数获取指定Header值
  * 属性：`value`用于指定Header的键值
* `@CookieValue`：指定当前控制器方法参数获取Cookie值
  * 属性：`value`用于指定Cookie的键值
* `@ModelAttribute`：指定当前方法先于当前控制器每个方法执行之前执行，如果有返回值，则自动将该返回值加入到`ModelMap`中。
  * 修饰方法时，`value`用于指定存入`Model`中的键值对的`key`值（键值对的值为函数返回值），若未指定则使用默认值
  * 修饰参数时，`value`用于指定取出`Model`中的键值为`key`的值
* `@SessionAttributes`：指定当前类存入`Model`中的某参数至session域
  * 属性：`value`用于指定`Model`中的某参数名称（并将其存入session域）
* `@RestController`：指定当前类为Rest风格控制器（相当于`@ResponseBody` + `@Controller`）
* `@RestControllerAdvice`：指定当前类为Rest风格异常控制器（相当于`@ResponseBody` + `@ControllerAdvice`）
* `@ExceptionHandler`：指定当前控制器方法处理指定类型错误

## Spring Boot

Spring 传统开发最让人头疼的就是配置和依赖，Spring Boot 就是为了解决这俩痛点来的。

* Spring Boot文档：https://spring.io/projects/spring-boot#learn
* Spring传统缺点：
  * 配置繁琐：SpringBoot采用自动配置技术
  * 依赖繁琐：SpringBoot采用起步依赖技术
* Spring Boot优点：Spring Boot并不是对Spring功能上的增强，而是提供了一种快速使用Spring的方式。
  * 自动配置
  * 起步依赖
  * 辅助功能
* Parent：开发Spring Boot应用需继承`spring-boot-starter-parent`（Spring Boot父工程）。
  * `spring-boot-starter-parent`定义了若干坐标版本号，以达到减少依赖冲突的目的。
  * `spring-boot-starter-parent`各版本间存在诸多坐标版本不同。

* Starter：开发Spring Boot应用需导入若干starter（starter根据功能不同通常会包含多个依赖坐标）。
  * starter定义了当前项目使用的所有依赖坐标，以达到减少依赖配置的目的。
  * 依赖配置使用任意坐标时，仅书写GA即可（V由Spring Boot提供），若Spring Boot未提供V则指定V（要小心版本冲突）。

* 引导类：Spring Boot应用的入口需使用`@SpringBootApplication`注解。
  * Spring Boot应用提供引导类用来启动程序，运行引导类的`main`方法可以启动项目。
  * Spring Boot应用运行后会初始化Spring容器（`ConfigurableApplicationContext`），扫描引导类所在包并加载bean。

* Profile：Profile是用来完成不同环境下、配置动态切换功能的。
  * 配置方式：多profile方式、yml多文档方式
  * 激活方式：配置文件（`spring.profiles.active=dev`）、虚拟机参数（`-Dspring.profiles.active=dev`）、命令行参数（`java -jar xxx.jar --spring.profiles.active=dev`）

### 配置文件

* `application.properties`：优先级高于`application.yml`

```properties
server.port=8080
server.servlet.context-path=/hello
```

* `application.yml`：大小写敏感、使用空格缩进表示层级关系（数据值前**必须**有空格）、可以表示对象/数组/纯量

```yml
server:
  port: 8080
  servlet:
    context-path: /hello
```

属性具体用法参考[官方文档](https://docs.spring.io/spring-boot/docs/current/reference/html/application-properties.html)，配置文件优先级为`application.properties` > `application.yml` > `application.yaml`，不同配置文件相同配置按加载优先级相互覆盖，不同配置文件中不同配置全部保留。

### 读取配置

* `@Value`：引用读取自定义配置，可以直接引用（`${name}`）、对象引用（`${person.name}`）、数组引用（`${address1[0]}`）

```java
@Value("${name}")
private String name;
```

* `org.springframework.core.env.Environment`：`getProperty`方法读取自定义配置

```java
@Autowired
private Environment env; // String getProperty(String key);
```

* `@ConfigurationProperties`：配置绑定（与自定义配置绑定）

```java
@Autowired
private Person person;
/**
 * @Component // 定义数据模型为Spring管控的Bean
 * @ConfigurationProperties(prefix = "person") // 指定被加载的属性
 * public class Person implements Serializable { // 定义数据模型封装YAML中对应数据
 *     private String name;
 *     private Integer age;
 *
 *     public String getName() {
 *         return name;
 *     }
 *
 *     public void setName(String name) {
 *         this.name = name;
 *     }
 *
 *     public Integer getAge() {
 *         return age;
 *     }
 *
 *     public void setAge(Integer age) {
 *         this.age = age;
 *     }
 *
 *     @Override
 *     public String toString() {
 *         return "Person{" +
 *                 "name='" + name + '\'' +
 *                 ", age=" + age +
 *                 '}';
 *     }
 * }
 */
```

### Profile

* 多profile文件方式：提供多个配置环境，每个文件代表一个环境

`application-dev.properties`：

```properties
server.port=8081
```

`application-test.properties`：

```properties
server.port=8082
```

`application-pro.properties`：

```properties
server.port=8083
```

`application.properties`：

```properties
spring.profiles.active=dev
```

* yml多文档方式：使用`---`分隔不同配置

```yml
---
server:
  port: 8081

spring:
  profiles: dev
---
server:
  port: 8082

spring:
  profiles: test
---
server:
  port: 8083

spring:
  profiles: pro
---
spring:
  profiles:
    active: test
```

### 加载顺序

* 内部配置加载顺序：从上至下依次加载。

1. file:./config/当前项目config目录下
2. file:./当前项目根目录
3. classpath:/config/类路径的config目录
4. classpath:/类路径的根目录

## SSM整合

SSM = Spring + SpringMVC + Mybatis，老三样了。整合思路其实就一句话：各管各的——Spring 管对象，SpringMVC 管请求，Mybatis 管数据库，再把它们串起来。下面是完整步骤：

### 环境搭建

1. 导入相关依赖

```xml
<!-- 必须配置 -->
<!-- spring-context 提供IoC核心容器 -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-context -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-context</artifactId>
    <version>5.2.9.RELEASE</version>
</dependency>
<!-- aspectjweaver 提供AOP编程 -->
<!-- https://mvnrepository.com/artifact/org.aspectj/aspectjweaver -->
<dependency>
    <groupId>org.aspectj</groupId>
    <artifactId>aspectjweaver</artifactId>
    <version>1.9.6</version>
    <scope>runtime</scope>
</dependency>
<!-- Spring-tx 提供事务控制 -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-tx -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-tx</artifactId>
    <version>5.2.18.RELEASE</version>
</dependency>

<!-- 可能配置 -->
<!-- spring-mvc -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-webmvc -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-webmvc</artifactId>
    <version>5.0.2.RELEASE</version>
</dependency>
<!-- spring-test 用于整合JUnit -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-test -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-test</artifactId>
    <version>5.2.18.RELEASE</version>
    <scope>test</scope>
</dependency>
<!-- spring-jdbc JDBC相关 -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-jdbc -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-jdbc</artifactId>
    <version>5.2.18.RELEASE</version>
</dependency>
```

2. 配置`applicationContext.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:context="http://www.springframework.org/schema/context"
       xmlns:aop="http://www.springframework.org/schema/aop"
       xmlns:tx="http://www.springframework.org/schema/tx"
       xmlns:mvc="http://www.springframework.org/schema/mvc"
       xsi:schemaLocation="http://www.springframework.org/schema/beans
                           https://www.springframework.org/schema/beans/spring-beans.xsd
                           http://www.springframework.org/schema/context
                           https://www.springframework.org/schema/context/spring-context.xsd
                           http://www.springframework.org/schema/tx
                           http://www.springframework.org/schema/tx/spring-tx.xsd
                           http://www.springframework.org/schema/mvc
                           http://www.springframework.org/schema/mvc/spring-mvc.xsd
">

    <!-- bean definitions go here -->

</beans>
```

3. 配置`applicationContext.xml`，开启注解扫描包

```xml
<!-- 开启注解扫描包 -->
<context:component-scan base-package="com.lee" >
    <!-- 配置对某些注解不扫描 -->
    <context:exclude-filter type="annotation" expression="org.springframework.stereotype.Controller"/>
    <!-- 配置只对某些注解扫描
    <context:include-filter type="annotation" expression="org.springframework.stereotype.Controller"/>
    -->
</context:component-scan>
```

4. 相应类中添加`@Repository`、`@Service`、`@Controller`、`@Component`注解

### 集成Druid

1. 导入相关依赖

```xml
<!-- mysql mysql驱动 -->
<!-- https://mvnrepository.com/artifact/mysql/mysql-connector-java -->
<dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
    <version>8.0.16</version>
</dependency>
<!-- druid Druid数据源 -->
<!-- https://mvnrepository.com/artifact/com.alibaba/druid -->
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>druid</artifactId>
    <version>1.2.8</version>
</dependency>
```

2. 配置`db.properties`

```properties
######## Database configuration information ########
druid.driverClassName=com.mysql.cj.jdbc.Driver
druid.url=jdbc:mysql://localhost:3306/test?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf8
druid.username=root
druid.password=123456
```

3. 配置`applicationContext.xml`

```xml
<!-- 读取配置文件 -->
<context:property-placeholder location="classpath:database_conf/db.properties"/>
```

```xml
<!-- Druid数据源 -->
<bean id="dataSource" class="com.alibaba.druid.pool.DruidDataSource">
    <property name="driverClassName" value="${druid.driverClassName}"/>
    <property name="url" value="${druid.url}"/>
    <property name="username" value="${druid.username}"/>
    <property name="password" value="${druid.password}"/>
</bean>
```

### 集成JUnit

1. 导入相关依赖

```xml
<!-- 必须配置 -->
<!-- JUnit 单元测试 -->
<!-- https://mvnrepository.com/artifact/junit/junit -->
<dependency>
    <groupId>junit</groupId>
    <artifactId>junit</artifactId>
    <version>4.12</version>
    <scope>test</scope>
</dependency>
<!-- spring-test 集成JUnit -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-test -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-test</artifactId>
    <version>5.2.18.RELEASE</version>
    <scope>test</scope>
</dependency>
```

2. 测试类添加`@RunWith(SpringJUnit4ClassRunner.class)`替换原先运行期（使用`@RunWith`替换原JUnit的`main`方法）
3. 测试类添加`@ContextConfiguration(...)`指定配置文件或文件类（告知Spring的运行器容器的创建方式）
   1. 可使用`locations`告知XML配置文件
   2. 可使用`classes`告知注解类位置

```java
@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(locations="classpath:spring_conf/applicationContext.xml")
```

4. 测试类中添加测试变量并注入依赖（使用`@Autowired`注入）

```java
@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(locations="classpath:spring_conf/applicationContext.xml")
public class DataSourceTest {

    @Autowired
    private DruidDataSource dataSource;

    @Test
    public void testDataSource() throws SQLException {
        DruidPooledConnection connection = dataSource.getConnection();
        System.out.println(connection);
        connection.close();
    }
}
```

5. 编写并运行测试代码

### 集成Mybatis

1. 导入相关依赖

```xml
<!-- 必须配置 -->
<!-- mybatis 持久层框架 -->
<!-- https://mvnrepository.com/artifact/org.mybatis/mybatis -->
<dependency>
    <groupId>org.mybatis</groupId>
    <artifactId>mybatis</artifactId>
    <version>3.4.6</version>
</dependency>
<!-- mybatis-spring 集成mybatis -->
<!-- https://mvnrepository.com/artifact/org.mybatis/mybatis-spring -->
<dependency>
    <groupId>org.mybatis</groupId>
    <artifactId>mybatis-spring</artifactId>
    <version>1.3.2</version>
</dependency>
<!-- spring-jdbc JDBC相关 -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-jdbc -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-jdbc</artifactId>
    <version>5.2.18.RELEASE</version>
</dependency>

<!-- 可能配置 -->
<!-- mysql mysql驱动 -->
<!-- https://mvnrepository.com/artifact/mysql/mysql-connector-java -->
<dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
    <version>8.0.16</version>
</dependency>
<!-- druid Druid数据源 -->
<!-- https://mvnrepository.com/artifact/com.alibaba/druid -->
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>druid</artifactId>
    <version>1.2.8</version>
</dependency>
```

2. 配置`mybatis-config.xml`：

`mybatis-config.xml`：

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE configuration
        PUBLIC "-//mybatis.org//DTD Config 3.0//EN"
        "http://mybatis.org/dtd/mybatis-3-config.dtd">
<!-- Mybatis的主配置文件 -->
<configuration>
    <!-- 配置别名 -->
    <typeAliases>
        <package name="com.lee.pojo" />
    </typeAliases>
</configuration>
```

3. 配置`applicatioContext.xml`

```xml
<!-- 数据源相关-需提供数据库信息以配置连接池 -->
<!-- 读取配置文件
<context:property-placeholder location="classpath:database_conf/db.properties"/>
-->
<!-- Druid数据源
<bean id="dataSource" class="com.alibaba.druid.pool.DruidDataSource">
    <property name="driverClassName" value="${druid.driverClassName}"/>
    <property name="url" value="${druid.url}"/>
    <property name="username" value="${druid.username}"/>
    <property name="password" value="${druid.password}"/>
</bean>
-->
```

```xml
<!-- 配置SqlSessionFactory -->
<bean id="sqlSessionFactory" class="org.mybatis.spring.SqlSessionFactoryBean"> <!-- 使用MP时类使用MybatisSqlSessionFactoryBean -->
    <!-- 注入数据源 -->
    <property name="dataSource" ref="dataSource"/>
    <!-- 指定MyBatis核心配置文件位置 -->
    <property name="configLocation" value="classpath:mybatis_conf/mybatis-config.xml"/>
    <!-- 指定Mapper映射文件位置 -->
    <property name="mapperLocations" value="classpath:mapper/*.xml"/>
</bean>

<!-- 扫描dao层 -->
<bean id="mapperScannerConfigurer" class="org.mybatis.spring.mapper.MapperScannerConfigurer">
    <property name="basePackage" value="com.lee.dao" />
</bean>
```

4. 编写实体类（pojo/domain/bean）

```java
package com.lee.pojo;

import java.io.Serializable;
import java.util.Date;

public class User implements Serializable {
    private Integer id;
    private String username;
    private Date birthday;
    private Character sex;
    private String address;

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public Date getBirthday() {
        return birthday;
    }

    public void setBirthday(Date birthday) {
        this.birthday = birthday;
    }

    public Character getSex() {
        return sex;
    }

    public void setSex(Character sex) {
        this.sex = sex;
    }

    public String getAddress() {
        return address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    @Override
    public String toString() {
        return "User{" +
                "id=" + id +
                ", username='" + username + '\'' +
                ", birthday=" + birthday +
                ", sex=" + sex +
                ", address='" + address + '\'' +
                '}';
    }
}
```

5. 编写持久层接口（dao/mapper）

6. 编写持久层类方法注解或持久层类的映射配置文件

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper
        PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
        "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<!-- 映射配置文件 -->
<mapper namespace="com.lee.dao.UserMapper"> <!-- namespace属性取值必须为dao接口的全限定类名 -->

    <!-- details -->

</mapper>
```

7. 持久层接口/类中添加`@Repository`注解

### 集成Spring MVC

1. 导入相关依赖

```xml
<!-- spring-mvc -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-webmvc -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-webmvc</artifactId>
    <version>5.0.2.RELEASE</version>
</dependency>
<!-- spring-web 提供核心的HTTP集成 -->
<!-- https://mvnrepository.com/artifact/org.springframework/spring-web -->
<dependency>
    <groupId>org.springframework</groupId>
    <artifactId>spring-web</artifactId>
    <version>5.0.2.RELEASE</version>
</dependency>
<!-- servlet-api 提供servlet支持 -->
<!-- https://mvnrepository.com/artifact/javax.servlet/javax.servlet-api -->
<dependency>
    <groupId>javax.servlet</groupId>
    <artifactId>javax.servlet-api</artifactId>
    <version>4.0.1</version>
    <scope>provided</scope>
</dependency>
<!-- jsp-api 提供jsp语法支持 -->
<!-- https://mvnrepository.com/artifact/javax.servlet.jsp/jsp-api -->
<dependency>
    <groupId>javax.servlet.jsp</groupId>
    <artifactId>jsp-api</artifactId>
    <version>2.1</version>
    <scope>provided</scope>
</dependency>
<!-- jstl -->
<!-- https://mvnrepository.com/artifact/javax.servlet/jstl -->
<dependency>
    <groupId>javax.servlet</groupId>
    <artifactId>jstl</artifactId>
    <version>1.2</version>
</dependency>
<!-- standard -->
<!-- https://mvnrepository.com/artifact/taglibs/standard -->
<dependency>
    <groupId>taglibs</groupId>
    <artifactId>standard</artifactId>
    <version>1.1.2</version>
</dependency>
<!-- jackson-databind -->
<!-- https://mvnrepository.com/artifact/com.fasterxml.jackson.core/jackson-databind -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
    <version>2.12.5</version>
</dependency>
<!-- jackson-core -->
<!-- https://mvnrepository.com/artifact/com.fasterxml.jackson.core/jackson-core -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-core</artifactId>
    <version>2.12.3</version>
</dependency>
<!-- jackson-annotations -->
<!-- https://mvnrepository.com/artifact/com.fasterxml.jackson.core/jackson-annotations -->
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-annotations</artifactId>
    <version>2.12.3</version>
</dependency>
<!-- commons-fileupload 提供文件上传 -->
<!-- https://mvnrepository.com/artifact/commons-fileupload/commons-fileupload -->
<dependency>
    <groupId>commons-fileupload</groupId>
    <artifactId>commons-fileupload</artifactId>
    <version>1.3.1</version>
</dependency>
<!-- commons-logging 日志组件 -->
<!-- https://mvnrepository.com/artifact/commons-logging/commons-logging -->
<dependency>
    <groupId>commons-logging</groupId>
    <artifactId>commons-logging</artifactId>
    <version>1.2</version>
</dependency>
```

2. 配置`web.xml`与`springmvc-config.xml`

`web.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<web-app xmlns="http://xmlns.jcp.org/xml/ns/javaee"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://xmlns.jcp.org/xml/ns/javaee
                      http://xmlns.jcp.org/xml/ns/javaee/web-app_4_0.xsd"
         version="4.0">
    <display-name>Archetype Created Web Application</display-name>
    <description>A simple student management system, created by ssm framework</description>

    <!-- 设置全局初始化参数 -->
    <context-param>
        <!-- 参数名 -->
        <param-name>contextConfigLocation</param-name>
        <!-- 注意: 使用classpath:path(防止FileNotFoundException) -->
        <param-value>classpath:spring_conf/applicationContext.xml</param-value>
    </context-param>

    <!-- 启动Spring: 配置加载Spring文件的监听器 -->
    <listener>
        <listener-class>org.springframework.web.context.ContextLoaderListener</listener-class>
    </listener>

    <!-- 启动Spring MVC: 部署DispatcherServlet -->
    <servlet>
        <!-- 配置Spring MVC的前端核心控制器 -->
        <servlet-name>dispatcherServlet</servlet-name>
        <servlet-class>org.springframework.web.servlet.DispatcherServlet </servlet-class>
        <!-- 加载Spring MVC配置文件 -->
        <init-param>
            <param-name>contextConfigLocation</param-name>
            <param-value>classpath:spring_conf/springmvc-config.xml</param-value>
        </init-param>
        <!-- 服务器启动后立即加载Spring MVC配置文件 -->
        <load-on-startup>1</load-on-startup>
    </servlet>
    <servlet-mapping>
        <servlet-name>dispatcherServlet</servlet-name>
        <url-pattern>/</url-pattern>
    </servlet-mapping>

    <!-- 配置Spring MVC编码过滤器 -->
    <filter>
        <filter-name>characterEncodingFilter</filter-name>
        <filter-class>org.springframework.web.filter.CharacterEncodingFilter</filter-class>
        <init-param>
            <param-name>encoding</param-name>
            <param-value>UTF-8</param-value>
        </init-param>
    </filter>
    <filter-mapping>
        <filter-name>characterEncodingFilter</filter-name>
        <url-pattern>/*</url-pattern>
    </filter-mapping>
    
    <!-- 欢迎页 -->
    <welcome-file-list>
        <welcome-file>index.jsp</welcome-file>
    </welcome-file-list>

</web-app>
```

`springmvc-config.xml`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xmlns:context="http://www.springframework.org/schema/context"
       xmlns:mvc="http://www.springframework.org/schema/mvc"
       xsi:schemaLocation="http://www.springframework.org/schema/beans
                           https://www.springframework.org/schema/beans/spring-beans.xsd
                           http://www.springframework.org/schema/context
                           https://www.springframework.org/schema/context/spring-context.xsd
                           http://www.springframework.org/schema/mvc
                           http://www.springframework.org/schema/mvc/spring-mvc.xsd
">

    <description>Spring-MVC configuration file</description>

    <!-- 开启注解扫描的包 -->
    <context:component-scan base-package="com.lee">
        <!-- 配置只扫描的注解 -->
        <context:include-filter type="annotation" expression="org.springframework.stereotype.Controller"/>
    </context:component-scan>

    <!-- 开启注解配置MVC -->
    <mvc:annotation-driven/>

    <!-- 处理静态资源 -->
    <mvc:default-servlet-handler/>

    <!-- 配置视图解析器 -->
    <bean id="internalResourceViewResolver" class="org.springframework.web.servlet.view.InternalResourceViewResolver">
        <!-- 前缀 -->
        <property name="prefix" value="/WEB-INF/view/"/>
        <!-- 后缀 -->
        <property name="suffix" value=".jsp"/>
    </bean>

</beans>
```

3. `AdminController`中添加`AdminService`

```java
@Autowired
private AdminService adminService;
```

## Spring Boot

### 环境搭建

前面讲了 Spring Boot 的概念，这里是实战：从零搭一个能跑的 Spring Boot 项目。

1. 导入父工程、起步依赖以及插件

```xml
<!-- Spring Boot父工程 -->
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.6.3</version>
    <relativePath/> <!-- lookup parent from repository -->
</parent>
```

```xml
<!-- spring-boot-starter-web Web应用 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
<!-- spring-boot-starter-test 测试 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>

<!-- 可能配置(web中已包含此依赖) -->
<!-- spring-boot-starter SpringBoot应用 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
</dependency>
```

```xml
<!-- Springboot插件 -->
<build>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
    </plugins>
</build>
```

2. 定义Controller

```java
package com.lee.controller;

import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController // 相当于@ResponseBody + @Controller
public class HelloController {

    @RequestMapping("/hello")
    public String hello() {
        return "Hello springboot!";
    }
}
```

3. 编写引导类

```java
package com.lee;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 引导类-SpringBoot项目入口
 */
@SpringBootApplication // 告知这是一个Spring Boot应用
public class MyApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyApplication.class, args);
    }
}
```

4. 启动测试

### 集成Lombok

1. 导入起步依赖

```xml
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
</dependency>
```

2. 实体类添加数据库表列名字段的对应属性
3. 实体类添加`@Data`注解，Lombok自动提供getter、setter、`toString`、`hashCode`、`equals`等方法（pojo/domain/bean）

### 集成Druid

1. 导入起步依赖

```xml
<!-- druid-spring-boot-starter Druid数据源 -->
<!-- https://mvnrepository.com/artifact/com.alibaba/druid-spring-boot-starter -->
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>druid-spring-boot-starter</artifactId>
    <version>1.2.8</version>
</dependency>
<!-- mysql mysql驱动 -->
<!-- https://mvnrepository.com/artifact/mysql/mysql-connector-java -->
<dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
    <scope>runtime</scope>
</dependency>
```

2. 配置`application.yml`

```yml
spring:
  datasource:
    druid:
      driver-class-name: com.mysql.cj.jdbc.Driver
      url: jdbc:mysql://localhost:3306/test?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf8
      username: root
      password: 123456
```

### 集成JUnit

1. 导入起步依赖

```xml
<!-- spring-boot-starter-test 测试 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
```

2. 测试类添加`@SpringBootTest`注解，必要时（测试类不存在于引导类所在的包或子包）使用`classes`属性指定引导类位置（`@SpringBootTest(classes = MyApplication.class)`）

```java
@RunWith(SpringRunner.class)
@SpringBootTest(classes = MyApplication.class)
```

3. 测试类中添加测试变量并注入依赖（使用`@Autowired`注入）

```java
@SpringBootTest(classes = MyApplication.class)
class MyApplicationTests {

    @Autowired
    private BookDao bookDao;

    @Test
    void testSave() {
        bookDao.save();
    }

}
```

4. 编写并运行测试代码

### 集成Mybatis

1. 导入起步依赖

```xml
<!-- mybatis-plus-boot-starter Mybatis Plus -->
<!-- https://mvnrepository.com/artifact/com.baomidou/mybatis-plus-boot-starter -->
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>mybatis-plus-boot-starter</artifactId>
    <version>3.4.2</version>
</dependency>

<!-- 可能配置 -->
<!-- mysql mysql驱动 -->
<!-- https://mvnrepository.com/artifact/mysql/mysql-connector-java -->
<dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
    <scope>runtime</scope>
</dependency>
<!-- druid-spring-boot-starter Druid数据源 -->
<!-- https://mvnrepository.com/artifact/com.alibaba/druid-spring-boot-starter -->
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>druid-spring-boot-starter</artifactId>
    <version>1.2.8</version>
</dependency>
<!-- mybatis-spring-boot-starter Mybatis -->
<!-- https://mvnrepository.com/artifact/org.mybatis.spring.boot/mybatis-spring-boot-starter -->
<dependency>
    <groupId>org.mybatis.spring.boot</groupId>
    <artifactId>mybatis-spring-boot-starter</artifactId>
    <version>2.2.2</version>
</dependency>
```

2. 配置`application.yml`

```yml
#spring:
#  datasource:
#    druid:
#      driver-class-name: com.mysql.cj.jdbc.Driver
#      url: jdbc:mysql://localhost:3306/test?serverTimezone=Asia/Shanghai&useUnicode=true&characterEncoding=utf8
#      username: root
#      password: 123456

# Mybatis Plus
mybatis-plus:
  global-config:
    db-config:
      table-prefix: tb_
      id-type: auto
```

3. 编写实体类（若使用Lombok则实体类直接添加`@Data`注解），**需使用`@TableName`指定表名**（pojo/domain/bean）

4. 编写持久层接口（若使用Mybatis Plus则可直接继承`BaseMapper<T>`），**需使用`@Mapper`注解标明此类**（dao/mapper）
5. 编写持久层类方法注解或持久层类的映射配置文件

差不多就这些，从 Spring 到 Spring Boot 的常见内容都过了一遍。祝写代码不报错——真有报错的话，就交给 agent 工具吧。
